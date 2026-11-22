"""Project configuration (`.devpipe/config.json`).

Purpose: one place for limits, adapter choice and agent names, with defaults
merged under whatever the project file states.
Side effects: `save` writes the file; nothing else touches disk.
"""
from __future__ import annotations

import copy
import json
import platform
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_DIR = ".devpipe"
CONFIG_FILE = "config.json"

# Limits come from the signed-off architecture (design/PIPELINE-ARCHITECTURE.md §11);
# the read and line limits are starting values that the dry run calibrates.
# Ticket size follows the tier a project executes on (design D-26). `constrained` is the
# limits below, sized for a small local model; a project planned on Claude and executed
# there needs none of that smallness, and pays for it in seams between tickets. A value the
# project sets itself under "limits" wins over its profile's.
PROFILES: Dict[str, Dict[str, Any]] = {
    "constrained": {},
    "claude": {"read_tokens": 60000, "max_writes": 3, "max_tests": 2, "write_lines": 400, "ticket_tokens": 2000},
}
DEFAULT_PROFILE = "constrained"

DEFAULTS: Dict[str, Any] = {
    "version": 1,
    "slug": "",
    # "constrained" or "claude"; a project without the key is constrained.
    "profile": "",
    "adapter": "opencode",
    "model": "",
    "opencode_bin": "",
    "claude_bin": "claude",
    "agents": {"engineer": "", "reviewer": "", "diagnostic": ""},
    "limits": {
        "read_tokens": 15000,
        # Largest ticket file. 900 was the first value; tickets that build a screen need more
        # room for what the screen shows, and an agent spent a session shaving them to fit.
        "ticket_tokens": 1200,
        "write_lines": 200,
        "max_writes": 1,
        "max_tests": 1,
        "diagnostic_cycles": 2,
        "review_retries": 1,
        "step_timeout_s": 1800,
        "verify_timeout_s": 900,
        # Limit an agent is told to put on its own run of a ticket's verify command;
        # 0 leaves the line out of the prompt. The runner's own verify uses the one above.
        "agent_verify_timeout_s": 60,
        "log_tail_lines": 120,
        # More plan steps than this and a feature is a plan revision; `lint features` says so.
        "feature_max_steps": 5,
    },
    "scope_allow": [],
    "phase_gate": [],
    # Regular expressions, tried on each line a phase-gate command prints. A match means the
    # command reused an earlier result and did not run its tests, and the gate is then not green.
    # These are added to the built-in ones for Gradle's JVM test tasks (runner.GATE_STALE).
    "phase_gate_stale": [],
    # Whole-repository commands too long to pay for at every completion of a phase: device suites,
    # performance tests. They run only at a seam (before the exit demo, at the phase's first
    # completion, and in `devpipe gate` before the merge), and like `phase_gate` commands never on a
    # tree that has already passed them (design D-32).
    "seam_gate": [],
    # Path patterns for files no gate command reads, besides the runner's own (tickets, ledgers,
    # briefs, HANDOFF.md). A commit that changes only such files leaves a green gate green.
    # A project whose checks read no document names its documents here.
    "phase_gate_ignore": [],
    # A shell command that exits 0 when the machine can build and test the project (Docker up, SDK
    # present). The runner runs it before the first ticket, and again when a ticket's verify fails:
    # a failure stops the run as infrastructure (exit 3) instead of blocking tickets. Empty: no check.
    "environment_check": "",
    # Path prefix -> test task. A ticket writing under the prefix must run that task whole in its
    # verify, never filtered with --tests: a hand-picked list misses the tests the gate then fails.
    "whole_suite": {},
    # `devpipe run --jobs N`: tickets that share no file run at the same time, each in its
    # own git worktree. Not for the opencode adapter, whose one local model serves one call.
    "parallel": {
        "jobs": 1,
        # Where the worktrees go; empty means ../.devpipe-worktrees/<project folder>/.
        "worktree_dir": "",
        # Untracked files a build needs, copied from the project into each worktree.
        "copy": ["local.properties"],
        # Patterns matched against a ticket's verify command: two tickets that match never
        # run at the same time (one emulator, one database, one port).
        "exclusive": [],
        # Run verify again on the phase branch when other tickets landed during the attempt.
        "reverify": True,
        "integration_retries": 1,
    },
    "tokens": {
        "url": "http://127.0.0.1:8080",
        "model": "",
        "key_env": "STRATA_API_KEY",
        "opencode_config": "~/.config/opencode/opencode.json",
        "provider": "strata",
    },
    "claude": {
        # false: agent calls use the Claude Code login (subscription); an API key in the
        # environment is not passed on. true: the key is passed on and billed.
        "use_api_key": False,
        # Model per role (a name for `claude --model`); empty falls back to "model", then to
        # the CLI's default. Give the reviewer a different one than the engineer.
        "models": {"engineer": "", "reviewer": "", "diagnostic": ""},
        # Effort per role (`claude --effort`); empty leaves the CLI's default.
        "effort": {"engineer": "", "reviewer": "", "diagnostic": ""},
        "engineer_tools": ["Read", "Edit", "Write", "Grep", "Glob", "Bash"],
        "reviewer_tools": ["Read", "Grep", "Glob", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)"],
        # The Diagnostic must run the ticket's verify command, so it gets the shell;
        # the runner undoes any file change it makes.
        "diagnostic_tools": ["Read", "Grep", "Glob", "Bash"],
        "deny_tools": [
            "Bash(git push:*)", "Bash(git reset --hard:*)", "Bash(git clean:*)",
            "Bash(git commit:*)", "Bash(sudo:*)", "WebFetch", "WebSearch", "Agent", "Skill",
        ],
    },
}


class ConfigError(ValueError):
    """The project is not set up, or its config file is not valid JSON."""


def _merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def find_root(start: Optional[Path] = None) -> Optional[Path]:
    """Return the nearest ancestor holding `.devpipe/config.json`, or None."""
    here = (start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / CONFIG_DIR / CONFIG_FILE).is_file():
            return candidate
    return None


def load(root: Path) -> Dict[str, Any]:
    """Return the project config merged over DEFAULTS."""
    path = root / CONFIG_DIR / CONFIG_FILE
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigError(f"{path} is missing; run `devpipe doctor`") from error
    except json.JSONDecodeError as error:
        raise ConfigError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(stored, dict):
        raise ConfigError(f"{path} must hold a JSON object")
    profile = str(stored.get("profile") or DEFAULT_PROFILE)
    if profile not in PROFILES:
        raise ConfigError(f"{path}: profile {profile!r} must be one of {', '.join(PROFILES)}")
    config = copy.deepcopy(DEFAULTS)
    config["limits"].update(PROFILES[profile])
    _merge(config, stored)
    config["profile"] = profile
    return config


def limit_sources(root: Path) -> Dict[str, str]:
    """Where each limit in force comes from: the project's file, its profile, or the default."""
    stored = json.loads((root / CONFIG_DIR / CONFIG_FILE).read_text(encoding="utf-8"))
    own = stored.get("limits") if isinstance(stored.get("limits"), dict) else {}
    profile = PROFILES[load(root)["profile"]]
    return {key: "set in .devpipe/config.json" if key in own else "from the profile" if key in profile else "default"
            for key in DEFAULTS["limits"]}


def save(root: Path, data: Dict[str, Any]) -> None:
    """Write the config file, creating `.devpipe/` when needed."""
    folder = root / CONFIG_DIR
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CONFIG_FILE).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def host_kind() -> str:
    """Return `mac` or `linux`, the vocabulary of a ticket's `host:` field."""
    return "mac" if platform.system() == "Darwin" else "linux"
