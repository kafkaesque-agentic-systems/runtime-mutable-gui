"""Adapters: one model call, as one fresh process, for one agent.

Purpose: hide the difference between `opencode run` and `claude -p` from the
runner. Every call starts a new process, so no conversation survives between
steps; agents communicate only through files.
Dependencies: the `opencode` or `claude` binary, found at call time.
Side effects: starts that process in the project folder and writes its raw
output to the log path given by the caller.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

OK, OVERSIZE, INFRA = "ok", "oversize", "infra"

# Text that marks "the window or the reply ran out", as opposed to a tool or
# network failure. Checked against error messages only, never against answers.
_OVERSIZE = re.compile(r"context|window|too (long|large)|max.?tokens|prompt is too|exceed", re.IGNORECASE)


@dataclass
class Result:
    """Outcome of one agent call."""

    kind: str            # ok | oversize | infra
    text: str = ""       # the agent's final message
    tokens_in: int = 0   # largest single prompt the model saw during the call; 0 when the tool does not say
    tokens_out: int = 0  # total tokens it wrote
    detail: str = ""     # why, when kind is not ok
    # Input of every request of the call added up, cache reads included: what the call cost to
    # read, not how full the window got. A 30-turn call re-reads its context 30 times.
    tokens_total: int = 0


class Adapter:
    """Interface: run `agent` on `prompt` in `root`."""

    name = "base"

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def check(self) -> str:
        """Return an empty string when usable, else what the owner must do."""
        raise NotImplementedError

    def run(self, role: str, agent: str, prompt: str, root: Path, log: Path, timeout: int) -> Result:
        raise NotImplementedError


def _execute(command: List[str], root: Path, log: Path, timeout: int,
             drop_env: Sequence[str] = ()) -> "subprocess.CompletedProcess[str]":
    log.parent.mkdir(parents=True, exist_ok=True)
    # DEVPIPE_AGENT=1 reaches the agent's shell; the project's git hooks refuse
    # commits and pushes while it is set.
    env = {key: value for key, value in os.environ.items() if key not in drop_env}
    env["DEVPIPE_AGENT"] = "1"
    # stdin is closed: `opencode run` waits on it forever when it is not a terminal.
    done = subprocess.run(command, cwd=str(root), capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, env=env)
    log.write_text(done.stdout + ("\n--- stderr ---\n" + done.stderr if done.stderr else ""), encoding="utf-8")
    return done


class OpenCodeAdapter(Adapter):
    """`opencode run --agent … --format json --auto --archived`."""

    name = "opencode"

    def binary(self) -> str:
        configured = os.environ.get("DEVPIPE_OPENCODE") or str(self.config.get("opencode_bin") or "")
        if configured:
            return os.path.expanduser(configured)
        on_path = shutil.which("opencode")
        if on_path:
            return on_path
        # The desktop app installs the server-side binary under a versioned folder.
        installed = glob.glob(os.path.expanduser("~/.opencode/desktop-ssh/*/opencode"))

        def version_key(path: str) -> List[int]:
            return [int(part) for part in re.findall(r"\d+", Path(path).parent.name)]

        return max(installed, key=version_key) if installed else ""

    def check(self) -> str:
        binary = self.binary()
        if not binary or not os.access(binary, os.X_OK):
            return "opencode binary not found: set opencode_bin in .devpipe/config.json"
        if not self.config.get("model"):
            return "no model set: put provider/model in .devpipe/config.json"
        if shutil.which("strata"):
            done = subprocess.run(["strata", "connect", "opencode", "--check", "--output", "json"],
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL)
            if done.returncode != 0:
                return "the Strata server did not pass its check: start it with `strata launch`, then run again"
        return ""

    def run(self, role: str, agent: str, prompt: str, root: Path, log: Path, timeout: int) -> Result:
        # `--auto` approves only what the agent's own rules do not deny; each
        # generated agent starts from deny-all, so nothing is left to "ask".
        command = [self.binary(), "run", "--agent", agent, "--model", str(self.config["model"]),
                   "--format", "json", "--auto", "--archived", "--title", f"devpipe {role}", prompt]
        try:
            done = _execute(command, root, log, timeout)
        except subprocess.TimeoutExpired:
            return Result(INFRA, detail=f"{role} call exceeded {timeout}s")
        except OSError as error:
            return Result(INFRA, detail=f"cannot start opencode: {error}")
        return self.parse(done.stdout, done.stderr, done.returncode)

    @staticmethod
    def parse(stdout: str, stderr: str, code: int) -> Result:
        """Fold OpenCode's JSON event lines into a Result."""
        text, finish, errors = "", "", []
        tokens_in = tokens_out = tokens_total = 0
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            part = event.get("part") or {}
            kind = event.get("type")
            if kind == "text":
                text = str(part.get("text", ""))
            elif kind == "step_finish":
                usage = part.get("tokens") or {}
                cache = usage.get("cache") or {}
                step_in = int(usage.get("input", 0)) + int(cache.get("read", 0))
                tokens_in = max(tokens_in, step_in)
                tokens_total += step_in
                tokens_out += int(usage.get("output", 0)) + int(usage.get("reasoning", 0))
                finish = str(part.get("reason", ""))
            elif kind == "error":
                errors.append(json.dumps(event.get("error") or part or event)[:600])
        if errors:
            detail = "; ".join(errors)
            return Result(OVERSIZE if _OVERSIZE.search(detail) else INFRA, text, tokens_in, tokens_out, tokens_total=tokens_total, detail=detail)
        if finish == "length":
            return Result(OVERSIZE, text, tokens_in, tokens_out, tokens_total=tokens_total, detail="the reply was cut at the output limit")
        if code != 0:
            return Result(INFRA, text, tokens_in, tokens_out, tokens_total=tokens_total, detail=f"opencode exited {code}: {stderr.strip()[-300:]}")
        if finish == "tool-calls":
            # The agent was still calling tools when its `steps` cap ended the run.
            return Result(OVERSIZE, text, tokens_in, tokens_out, tokens_total=tokens_total, detail="the agent's step cap ended the run before it finished")
        if finish != "stop":
            return Result(INFRA, text, tokens_in, tokens_out, tokens_total=tokens_total, detail=f"the run ended without a final answer (finish={finish or 'none'})")
        return Result(OK, text, tokens_in, tokens_out, tokens_total=tokens_total)


class ClaudeAdapter(Adapter):
    """`claude -p … --agent … --output-format json`."""

    name = "claude"

    def binary(self) -> str:
        configured = os.environ.get("DEVPIPE_CLAUDE") or str(self.config.get("claude_bin") or "claude")
        return shutil.which(os.path.expanduser(configured)) or ""

    def check(self) -> str:
        return "" if self.binary() else "claude binary not found: set claude_bin in .devpipe/config.json"

    def model_for(self, role: str) -> str:
        """Model a role runs on: `claude.models.<role>`, else `model`, else empty (the CLI's own default).

        Roles can differ so that the Reviewer is not the model that wrote the code.
        """
        settings = self.config.get("claude") or {}
        return str((settings.get("models") or {}).get(role) or self.config.get("model") or "")

    def command(self, role: str, agent: str, prompt: str) -> List[str]:
        """The `claude -p` command line for one call."""
        settings = self.config.get("claude") or {}
        tools = settings.get(f"{role}_tools") or []
        command = [self.binary(), "-p", prompt, "--agent", agent, "--output-format", "json",
                   "--permission-mode", "acceptEdits", "--no-session-persistence"]
        if self.model_for(role):
            command += ["--model", self.model_for(role)]
        effort = str((settings.get("effort") or {}).get(role) or "")
        if effort:
            command += ["--effort", effort]
        if tools:
            command += ["--allowedTools", *[str(tool) for tool in tools]]
        if settings.get("deny_tools"):
            command += ["--disallowedTools", *[str(tool) for tool in settings["deny_tools"]]]
        return command

    def run(self, role: str, agent: str, prompt: str, root: Path, log: Path, timeout: int) -> Result:
        settings = self.config.get("claude") or {}
        command = self.command(role, agent, prompt)
        # With an API key in the environment `claude -p` bills that key instead of the
        # owner's subscription login, so the key is withheld unless the config asks for it.
        withheld = () if settings.get("use_api_key") else ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
        try:
            done = _execute(command, root, log, timeout, drop_env=withheld)
        except subprocess.TimeoutExpired:
            return Result(INFRA, detail=f"{role} call exceeded {timeout}s")
        except OSError as error:
            return Result(INFRA, detail=f"cannot start claude: {error}")
        return self.parse(done.stdout, done.stderr, done.returncode)

    @staticmethod
    def parse(stdout: str, stderr: str, code: int) -> Result:
        """Read the single JSON result object `claude -p` prints."""
        try:
            payload = json.loads(stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return Result(INFRA, detail=f"claude printed no JSON result (exit {code}): {stderr.strip()[-300:]}")
        usage = payload.get("usage") or {}
        keys = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")

        def prompt(part: Any) -> int:
            return sum(int(part.get(key, 0) or 0) for key in keys) if isinstance(part, dict) else 0

        # `usage` adds up every request of the session, so it is the call's cost, not a prompt.
        # Single requests are under `usage.iterations`; the largest of those is the largest
        # prompt. In the results seen so far that list holds the call's last request, which is
        # its largest as long as the session was not compacted on the way. A result without
        # the list leaves the largest prompt unknown (0).
        tokens_total = prompt(usage)
        iterations = usage.get("iterations")
        tokens_in = max([prompt(part) for part in iterations] or [0]) if isinstance(iterations, list) else 0
        tokens_out = int(usage.get("output_tokens", 0))
        text = str(payload.get("result", ""))
        subtype = str(payload.get("subtype", ""))
        if payload.get("is_error") or subtype != "success" or code != 0:
            detail = f"{subtype or 'error'}: {text[:300]}"
            kind = OVERSIZE if subtype == "error_max_turns" or _OVERSIZE.search(detail) else INFRA
            return Result(kind, text, tokens_in, tokens_out, detail, tokens_total)
        return Result(OK, text, tokens_in, tokens_out, tokens_total=tokens_total)


class FakeAdapter(Adapter):
    """Scripted adapter for the toolkit's own tests; never selected by a stage.

    `DEVPIPE_FAKE_SCRIPT` names a JSON list. Each call consumes the next entry:
    `{"role": "engineer", "write": {"path": "content"}, "delete": ["path"],
    "text": "final message", "kind": "ok"}`.
    A JSON object keyed by ticket id (`{"P01-T02": [...]}`) gives each ticket its
    own list, for parallel runs where the order of calls across tickets is open.
    """

    name = "fake"

    def check(self) -> str:
        return "" if os.environ.get("DEVPIPE_FAKE_SCRIPT") else "DEVPIPE_FAKE_SCRIPT is not set"

    def run(self, role: str, agent: str, prompt: str, root: Path, log: Path, timeout: int) -> Result:
        script = Path(os.environ["DEVPIPE_FAKE_SCRIPT"])
        steps = json.loads(script.read_text(encoding="utf-8"))
        cursor = script.with_suffix(".pos")
        if isinstance(steps, dict):
            named = re.search(r"phase-(\d+)/ticket-(\d+)", prompt)
            key = f"P{named.group(1)}-T{named.group(2)}" if named else ""
            steps = steps.get(key, [])
            cursor = script.with_suffix(f".{key}.pos")
        position = int(cursor.read_text()) if cursor.exists() else 0
        if position >= len(steps):
            return Result(INFRA, detail=f"fake script exhausted at call {position} ({role})")
        step = steps[position]
        cursor.write_text(str(position + 1))
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(json.dumps({"role": role, "agent": agent, "prompt": prompt}), encoding="utf-8")
        if step.get("role") != role:
            return Result(INFRA, detail=f"fake script expected {step.get('role')} at call {position}, got {role}")
        for relative, content in (step.get("write") or {}).items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        for relative in step.get("delete") or []:
            (root / relative).unlink()
        if step.get("sleep"):
            time.sleep(float(step["sleep"]))  # lets a test stop the runner mid-call
        return Result(step.get("kind", OK), str(step.get("text", "")), int(step.get("tokens_in", 0)),
                      detail=str(step.get("detail", "")), tokens_total=int(step.get("tokens_total", 0)))


def make(config: Dict[str, Any]) -> Adapter:
    """Return the adapter named by the config."""
    kinds = {"opencode": OpenCodeAdapter, "claude": ClaudeAdapter, "fake": FakeAdapter}
    name = str(config.get("adapter", ""))
    if name not in kinds:
        raise ValueError(f"unknown adapter {name!r}; use opencode or claude")
    return kinds[name](config)
