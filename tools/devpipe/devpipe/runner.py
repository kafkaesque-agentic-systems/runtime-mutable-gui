"""The phase runner.

Purpose: execute one phase's tickets one at a time —
read budget -> Engineer -> scope check -> verify -> scope check ->
(Diagnostic -> Engineer) -> red check -> Reviewer -> commit — and stop cleanly
for the owner whenever a ticket blocks. A phase ends with its gate: whole-repository
commands, each run once per tree, the long ones only at a seam (design D-32). A ticket is measured and judged when it
starts, against the tree as it is then, not as it was when the ticket was written.
Pass or fail is the exit code of the ticket's `verify` command; a model's own
claim is never consulted.
Dependencies: adapters, gitutil, lint, report, tickets, config.
Side effects: runs agent processes and shell commands in the repository,
commits on the local `phase/NN` branch, resets the working tree to the
pre-ticket commit when a ticket blocks. Never pushes, pulls or merges.
"""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import adapters, config as cfg, features, gates, gitutil as git, lint, report, tickets as tk, tokens

EXIT_DONE, EXIT_OWNER, EXIT_INFRA = 0, 2, 3
STATE_FILE = ".run-state.json"
# The project's environment check is a few quick probes (`docker info`, an SDK path); a minute is generous.
ENVIRONMENT_CHECK_TIMEOUT_S = 60
# `devpipe pause` creates this file in the work folder; the run stops before its next ticket.
PAUSE_FILE = "pause"
BLOCKING_SEVERITIES = ("blocker", "major")
# A line like these in a phase-gate command's output says Gradle reused an earlier result for
# a JVM test task and ran no test. A project adds its own with `phase_gate_stale` (device tests,
# other build tools); other task names are too varied to guess.
GATE_STALE = (r"> Task \S*:test (UP-TO-DATE|FROM-CACHE)\s*$",
              r"> Task \S*:test\w*UnitTest (UP-TO-DATE|FROM-CACHE)\s*$")
DIAGNOSIS_MAX_LINES = 60
# An Engineer's final message says DONE or FAILED on a line of its own. Its verdict is the first
# such line, wherever it stands: an Engineer that explains itself before it says FAILED has still
# failed, and one that quotes a failing line after DONE has not.
VERDICT_LINE = re.compile(r"^\W{0,4}(DONE|FAILED)\b")
OWNER_HEADING = re.compile(r"^\W{0,4}for the owner\W{0,4}(.*)$", re.IGNORECASE)
OWNER_NOTES_FILE = "owner-notes.md"
OWNER_NOTES_MAX = 8


class Halt(Exception):
    """Stop the run; `code` is the process exit status."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


@dataclass
class Outcome:
    """How one attempt at a ticket ended, before anything is recorded in the repository.

    An attempt and its record are separate steps so that a parallel run can make
    the attempt in a worktree and record it on the phase branch.
    """

    kind: str                      # done | blocked
    reason: str = ""               # blocked: verify, red-check, review, malformed, oversize, ticket-defect, engineer-failed, integration
    detail: str = ""
    discarded: List[str] = field(default_factory=list)
    findings: int = 0              # minor findings the review left in review.json
    notes: List[str] = field(default_factory=list)      # anything else the ledger should say about the attempt
    stats: Dict[str, Any] = field(default_factory=dict)


def _say(message: str) -> None:
    print(f"devpipe: {message}", flush=True)


class Runner:
    """Runs one phase. Create, then call `run()`."""

    def __init__(self, root: Path, phase: int, continue_on_block: bool = False, max_tickets: int = 0):
        self.root = root
        self.phase = phase
        self.continue_on_block = continue_on_block
        self.max_tickets = max_tickets
        self.config = cfg.load(root)
        self.limits = self.config["limits"]
        self.adapter = adapters.make(self.config)
        self.host = cfg.host_kind()
        self.sequence = 0
        self.stats: Dict[str, Any] = {}
        self.base = ""
        self.counter = tokens.Counter(self.config.get("tokens") or {})

    # ------------------------------------------------------------ state file

    def _state(self, **fields: Any) -> None:
        path = self.root / tk.TICKET_DIR / STATE_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"phase": self.phase, "updated": report.now(), **fields}, indent=2) + "\n",
                        encoding="utf-8")

    def _pause_file(self) -> Path:
        return self.root / tk.TICKET_DIR / tk.WORK_DIR / PAUSE_FILE

    def _handoff(self, headline: str, owner_steps: List[str], gate_ran: bool = False) -> None:
        """Rewrite HANDOFF.md; the run's counter remembers sizes it has measured already."""
        report.handoff(self.root, self.config, self.phase, headline, owner_steps, self.counter, gate_ran)

    # -------------------------------------------------------------- preflight

    def preflight(self) -> None:
        root = self.root
        if not git.is_repo(root) or not git.has_commits(root):
            raise Halt(EXIT_OWNER, "this folder has no git history yet; the init stage creates the first commit")
        if not git.is_clean(root):
            raise Halt(EXIT_OWNER, "the working tree has uncommitted changes; commit or discard them, then run again")
        if self.config["profile"] == "claude" and self.adapter.name == "opencode":
            raise Halt(EXIT_OWNER, "this project's profile is `claude`: its tickets are sized for Claude Code and do not "
                                   "fit the local model. Run it with the claude adapter, or set \"profile\": \"constrained\" "
                                   "in .devpipe/config.json and write the unfinished tickets again")
        problem = self.adapter.check()
        if problem:
            raise Halt(EXIT_INFRA, problem)
        problem = self._environment_problem()
        if problem:
            raise Halt(EXIT_INFRA, f"{problem}; fix the machine, then run again (nothing was started)")
        issues = lint.lint_tickets(root, self.config, self.phase) + features.lint_features(root, self.config)
        if self.adapter.name != "fake":
            issues += [issue for issue in lint.lint_agents(root, self.config)
                       if lint.AGENT_DIRS[self.adapter.name] in issue.where or issue.where.startswith(".devpipe")]
        errors = [issue for issue in issues if issue.level == lint.ERROR]
        if errors:
            for issue in errors:
                print(issue)
            raise Halt(EXIT_OWNER, f"{len(errors)} lint error(s); fix them before the phase can run")
        if isinstance(self.adapter, adapters.ClaudeAdapter) \
                and self.adapter.model_for("engineer") == self.adapter.model_for("reviewer"):
            _say("note: engineer and reviewer run on the same model "
                 f"({self.adapter.model_for('engineer') or 'the CLI default'}); set claude.models.reviewer in "
                 ".devpipe/config.json so the review is independent")
        target = f"phase/{self.phase:02d}"
        if git.branch(root) != target:
            git.git(root, "switch", target) if git.branch_exists(root, target) else git.git(root, "switch", "-c", target)
            _say(f"on branch {target}")

    # ------------------------------------------------------------------ steps

    def _call(self, role: str, ticket: tk.Ticket, prompt: str) -> adapters.Result:
        self.sequence += 1
        log = ticket.work_dir(self.root) / f"{self.sequence:02d}-{role}.log"
        self._state(ticket=ticket.id, step=role, base=self.base, **self.stats)
        _say(f"{ticket.id} {role}")
        result = self.adapter.run(role, str(self.config["agents"][role]), prompt, self.root, log,
                                  int(self.limits["step_timeout_s"]))
        self.stats["max_tokens_in"] = max(self.stats.get("max_tokens_in", 0), result.tokens_in)
        self.stats["tokens_in_total"] = self.stats.get("tokens_in_total", 0) + result.tokens_total
        return result

    def _engineer_prompt(self, ticket: tk.Ticket, step: str, extra: str = "") -> str:
        lines = [f"TICKET {ticket.path.relative_to(self.root)}", f"STEP {step}"]
        if extra:
            lines.append(extra)
        lines.extend(self._verify_lines(ticket))
        return "\n".join(lines)

    def _verify_lines(self, ticket: tk.Ticket) -> List[str]:
        """Prompt lines naming the verify command and the time limit an agent puts on it.

        Without a limit a hanging implementation holds the agent's shell tool until the
        tool's own default expires, and the tool then suggests a longer one.
        """
        lines = [f"VERIFY {ticket.verify}"]
        seconds = int(self.limits.get("agent_verify_timeout_s", 60))
        if seconds > 0:
            lines.append(f"VERIFY_TIMEOUT_MS {seconds * 1000}")
        return lines

    @staticmethod
    def failure_report(said: str) -> str:
        """What an Engineer's FAILED report says, in at most three lines joined by ' / '; '' when its verdict is not FAILED."""
        lines = said.splitlines()
        for index, line in enumerate(lines):
            verdict = VERDICT_LINE.match(line)
            if verdict:
                if verdict.group(1) != "FAILED":
                    return ""
                return " / ".join(part.strip() for part in lines[index:] if part.strip())[:500] if index else \
                    " / ".join(part.strip() for part in lines[:3] if part.strip())[:500]
        return ""

    def _ticket_files(self, ticket: tk.Ticket) -> Dict[str, Optional[bytes]]:
        """The ticket's own files as they are now, to tell whether an Engineer call changed any of them."""
        found: Dict[str, Optional[bytes]] = {}
        for path in [*ticket.writes, *ticket.tests]:
            target = self.root / path
            found[path] = target.read_bytes() if target.is_file() else None
        return found

    def _keep_owner_notes(self, ticket: tk.Ticket, said: str) -> None:
        """Keep what an Engineer wrote under `For the owner:`; the next call's report replaces this one's.

        Seen in a pilot: reports held "this decision can't be followed as written, please confirm" and
        "the key file is not in .gitignore", and no brief, ledger or handoff repeated them. They
        were found at the retrospective. The lines are kept beside the logs and carried to
        `HANDOFF.md` and the review brief (report.owner_notes).
        """
        lines = said.splitlines()
        notes: List[str] = []
        for index, line in enumerate(lines):
            heading = OWNER_HEADING.match(line)
            if not heading:
                continue
            rest = [heading.group(1)] + lines[index + 1:]
            notes = [note for note in (re.sub(r"^[\s*•-]+", "", part).strip() for part in rest) if note][:OWNER_NOTES_MAX]
            break
        if not notes:
            return
        path = ticket.work_dir(self.root) / OWNER_NOTES_FILE
        kept = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
        path.write_text("\n".join(kept + [note for note in notes if note not in kept]) + "\n", encoding="utf-8")

    def _outside(self, allowed: Set[str]) -> List[str]:
        """Changed files that are neither in `allowed` nor matched by the project's scope_allow."""
        patterns = [str(pattern) for pattern in self.config.get("scope_allow") or []]
        return [path for path in git.changed_files(self.root)
                if path not in allowed and not any(fnmatch.fnmatch(path, pattern) for pattern in patterns)]

    def _enforce_scope(self, ticket: tk.Ticket, by: str = "") -> List[str]:
        """Discard changes outside the ticket's files; return what was discarded.

        Called after the Engineer and again after every run of the verify command (`by`
        names it): a build writes files too, and the commit takes whatever is in the tree.
        """
        outside = self._outside(set(ticket.writes) | set(ticket.tests))
        if outside:
            git.restore_paths(self.root, self.base, outside)
            _say(f"{ticket.id} discarded out-of-scope changes{' made by ' + by if by else ''}: {', '.join(outside)}")
        return outside

    def _read_budget(self, ticket: tk.Ticket) -> str:
        """Why the ticket's read manifest no longer fits, or '' when it does.

        The lint measured it when the run started; tickets that ran since then have
        extended the files it names.
        """
        total, sizes = lint.read_manifest_size(self.root, ticket, self.counter)
        limit = int(self.limits["read_tokens"])
        if total <= limit:
            return ""
        largest = ", ".join(label for _size, label in sizes[:3])
        return (f"its read manifest is now {total} tokens; the limit is {limit} (limits.read_tokens). The files it "
                f"reads have grown since the ticket was written; largest: {largest}. Narrow those `read:` entries "
                "to line ranges or sections; `devpipe reads` shows every unfinished ticket's size")

    def _shell(self, command: str, log: Path) -> int:
        """Run a shell command in the repository; write its output to `log`; return its exit code."""
        log.parent.mkdir(parents=True, exist_ok=True)
        try:
            done = subprocess.run(command, shell=True, cwd=str(self.root), capture_output=True, text=True,
                                  timeout=int(self.limits["verify_timeout_s"]), stdin=subprocess.DEVNULL)
            output, code = done.stdout + done.stderr, done.returncode
        except subprocess.TimeoutExpired as error:
            output = f"{error.stdout or ''}{error.stderr or ''}\n[devpipe] timed out after {self.limits['verify_timeout_s']}s\n"
            code = 124
        log.write_text(f"$ {command}\n{output}\n[exit {code}]\n", encoding="utf-8")
        return code

    def _environment_problem(self) -> str:
        """Run the project's `environment_check`; '' when it passes or none is set, else what failed.

        Seen in a pilot: a run started with the Docker daemon down. Five tickets blocked as ticket
        defects, each after an Engineer round and a Diagnostic, at about 5 million input tokens and
        with no test run. The project's own check named the cause in 0.3 seconds.
        """
        command = str(self.config.get("environment_check") or "").strip()
        if not command:
            return ""
        try:
            done = subprocess.run(command, shell=True, cwd=str(self.root), capture_output=True, text=True,
                                  timeout=ENVIRONMENT_CHECK_TIMEOUT_S, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return f"the environment check `{command}` did not finish within {ENVIRONMENT_CHECK_TIMEOUT_S}s"
        if done.returncode == 0:
            return ""
        lines = [line for line in (done.stdout + done.stderr).strip().splitlines() if line.strip()]
        said = "; ".join(lines[:5]) or "(it printed nothing)"
        return f"the environment check `{command}` exits {done.returncode}: {said}"

    def _verify(self, ticket: tk.Ticket) -> Tuple[int, Path]:
        self.sequence += 1
        self.stats["verify_runs"] = self.stats.get("verify_runs", 0) + 1
        log = ticket.work_dir(self.root) / f"{self.sequence:02d}-verify.log"
        code = self._shell(ticket.verify, log)
        tail = log.with_suffix(".tail.log")
        lines = log.read_text(encoding="utf-8").splitlines()
        tail.write_text("\n".join(lines[-int(self.limits["log_tail_lines"]):]) + "\n", encoding="utf-8")
        _say(f"{ticket.id} verify exit {code}")
        return code, tail

    def _red_command(self, ticket: tk.Ticket, discarded: List[str], notes: List[str]) -> str:
        """The command the red check runs: the ticket's `red_verify` once it has been seen to pass, else `verify`.

        Under `whole_suite` a ticket's verify is a module's whole test task, and running that with
        the implementation removed means a thousand tests to learn that three fail. A narrower
        command asks the same question, but only one that passes with the implementation in place
        proves anything by failing without it: a command that names a test which does not exist
        fails both times. Such a command is set aside, the ledger says so, and the red check runs
        `verify` as before. A wrong header costs minutes, never a blocked ticket.
        """
        if not ticket.red_verify.strip():
            return ticket.verify
        self.sequence += 1
        log = ticket.work_dir(self.root) / f"{self.sequence:02d}-red-verify.log"
        code = self._shell(ticket.red_verify, log)
        discarded += self._enforce_scope(ticket, by="the red_verify command")
        if code == 0:
            return ticket.red_verify
        note = f"red_verify exits {code} with the implementation in place, so the red check ran verify"
        _say(f"{ticket.id} {note}")
        if note not in notes:
            notes.append(note)
        return ticket.verify

    def _red_check(self, ticket: tk.Ticket, command: str = "") -> Tuple[bool, List[str]]:
        """Run `command` (the ticket's verify unless given) with the implementation removed.

        Returns (failed, rewritten): `failed` is True when the command fails, which is what a test
        that tests something does; `rewritten` lists the ticket's files that the command
        itself put back, in which case a pass says nothing about the test.
        """
        command = command or ticket.verify
        saved = {path: (self.root / path).read_bytes() for path in ticket.writes if (self.root / path).is_file()}
        self.sequence += 1
        log = ticket.work_dir(self.root) / f"{self.sequence:02d}-red-check.log"
        rewritten: List[str] = []
        try:
            git.restore_paths(self.root, self.base, ticket.writes)
            code = self._shell(command, log)
            rewritten = [path for path in ticket.writes if git.differs_from(self.root, self.base, path)]
        finally:
            for path, content in saved.items():
                target = self.root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        _say(f"{ticket.id} red check: {'verify' if command == ticket.verify else 'red_verify'} exit {code} "
             "without the implementation")
        return code != 0, rewritten

    def _read_only_call(self, role: str, ticket: tk.Ticket, prompt: str, patch: str) -> adapters.Result:
        """Call an agent that must not change the tree; undo anything it changed anyway."""
        result = self._call(role, ticket, prompt)
        if git.patch_against(self.root, self.base) != patch:
            _say(f"{ticket.id} the {role} changed files; restoring the engineer's work")
            saved = ticket.work_dir(self.root) / "restore.patch"
            saved.write_text(patch + "\n", encoding="utf-8")
            git.reset_to(self.root, self.base)
            if patch.strip():
                git.git(self.root, "apply", "--whitespace=nowarn", str(saved))
        return result

    # ------------------------------------------------------- reviewer verdict

    @staticmethod
    def changed_lines(patch: str) -> Dict[str, List[Tuple[int, int]]]:
        """Map each file in a unified diff to the [start, end] line ranges of its hunks."""
        ranges: Dict[str, List[Tuple[int, int]]] = {}
        current = ""
        for line in patch.splitlines():
            if line.startswith("+++ "):
                current = line[6:] if line.startswith("+++ b/") else ""
                if current:
                    ranges.setdefault(current, [])
            elif line.startswith("@@") and current:
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
                if match:
                    start, count = int(match.group(1)), int(match.group(2) or "1")
                    ranges[current].append((start, start + max(count, 1) - 1))
        return ranges

    @staticmethod
    def patch_lines(patch: str) -> Tuple[Dict[str, Dict[int, str]], Dict[int, Tuple[str, int]]]:
        """Two readings of a unified diff: ({file: {line in the new file: its text}},
        {line of the diff file itself, from 1: (file, line in the new file)}), for added and context lines."""
        by_file: Dict[str, Dict[int, str]] = {}
        by_diff_line: Dict[int, Tuple[str, int]] = {}
        current, new_line = "", 0
        for number, line in enumerate(patch.splitlines(), start=1):
            if line.startswith("+++ "):
                current = line[6:] if line.startswith("+++ b/") else ""
            elif line.startswith("@@") and current:
                match = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
                new_line = int(match.group(1)) if match else 0
            elif current and new_line and line[:1] in ("+", " ") and not line.startswith("+++"):
                by_file.setdefault(current, {})[new_line] = line[1:]
                by_diff_line[number] = (current, new_line)
                new_line += 1
            elif line.startswith("diff --git"):
                current, new_line = "", 0
        return by_file, by_diff_line

    @staticmethod
    def locate(finding: Dict[str, Any], ranges: Dict[str, List[Tuple[int, int]]],
               by_file: Dict[str, Dict[int, str]], by_diff_line: Dict[int, Tuple[str, int]]) -> Dict[str, Any]:
        """Put a finding's line right when the reviewer counted it in the diff file, not in the source file.

        For a new file every line is inside a hunk, so a line counted in the diff passes the hunk
        check and is recorded as fact, some hundreds of lines off. The same number read as a line of
        the diff names a line of the new file; where the finding quotes code (in backticks) that
        stands there and not at the line as given, or where the line as given is outside every
        hunk, the line is replaced and the number the reviewer wrote is kept as `line_cited`.
        """
        path, line = str(finding.get("file")), finding.get("line")
        if not isinstance(line, int):
            return finding
        other = by_diff_line.get(line)
        if not other or other[0] != path or other[1] == line:
            return finding
        quoted = [span.strip() for span in re.findall(r"`([^`\n]+)`", f"{finding.get('claim', '')} {finding.get('evidence', '')}")
                  if len(span.strip()) >= 6]

        def stands_near(where: int) -> bool:
            near = " ".join(by_file.get(path, {}).get(n, "") for n in range(where - 2, where + 3))
            return any(span in near for span in quoted)

        inside = any(low <= line <= high for low, high in ranges.get(path, []))
        if (not inside) or (stands_near(other[1]) and not stands_near(line)):
            return {**finding, "line": other[1], "line_cited": line}
        return finding

    @classmethod
    def parse_review(cls, text: str, patch: str) -> Optional[Dict[str, Any]]:
        """Validate the reviewer's JSON. Returns None when it is malformed.

        A finding survives only when it cites a file and line inside the diff;
        the verdict is CHANGES only when a blocker or major finding survives.
        """
        # The verdict is the last JSON object in the reply that carries one. A reviewer often
        # writes prose first, and prose about code has braces of its own (`.word { … }`), so
        # "from the first brace to the last" would read a passing review as malformed.
        decoder = json.JSONDecoder()
        data = None
        for start in (index for index, char in enumerate(text) if char == "{"):
            try:
                candidate, _end = decoder.raw_decode(text, start)
            except ValueError:
                continue
            if isinstance(candidate, dict) and candidate.get("verdict") in ("PASS", "CHANGES"):
                data = candidate
        if data is None or not isinstance(data.get("findings", []), list):
            return None
        ranges = cls.changed_lines(patch)
        by_file, by_diff_line = cls.patch_lines(patch)
        kept, dropped = [], []
        for finding in data.get("findings", []):
            if not isinstance(finding, dict):
                return None
            finding = cls.locate(finding, ranges, by_file, by_diff_line)
            line = finding.get("line")
            inside = isinstance(line, int) and any(low <= line <= high for low, high in ranges.get(str(finding.get("file")), []))
            if inside and str(finding.get("claim", "")).strip() and str(finding.get("evidence", "")).strip():
                kept.append(finding)
            else:
                dropped.append(finding)
        blocking = [finding for finding in kept if finding.get("severity") in BLOCKING_SEVERITIES]
        return {"verdict": "CHANGES" if blocking else "PASS", "stated_verdict": data["verdict"],
                "findings": kept, "dropped": dropped}

    def _rounds_compared(self, first: Dict[str, Any], last: Dict[str, Any]) -> str:
        """What a block after a second review round adds to its detail: both rounds, and whether they collide.

        Seen in a pilot: round 1 asked for a change, the Engineer made it, and round 2 rejected exactly
        that change as out of scope. The block quoted round 2 alone, and the triage had to read both
        files to see that the question was the ticket's, not the code's. A finding on a line the
        revision changed is either a fault in the fix or the two rounds asking for opposite things.
        """
        if not first:
            return ""
        number = first["round"]
        asked = "; ".join(str(finding.get("claim")) for finding in last["findings"][:3])
        text = f". Round {number} asked: {first['claims']}; round {number + 1} asks: {asked}".replace(
            f". Round {number} asked", f" — round {number} asked", 1)
        revised = self.changed_lines(git.git(self.root, "diff", "--cached", "-U0", first["tree"], check=False))
        hit = next((finding for finding in last["findings"] if finding.get("severity") in BLOCKING_SEVERITIES and any(
            low <= int(finding.get("line") or 0) <= high for low, high in revised.get(str(finding.get("file")), []))), None)
        if hit:
            text += (f". The finding at `{hit.get('file')}:{hit.get('line')}` is on a line the Engineer changed to answer "
                     f"round {number}: either that fix is wrong, or the two rounds ask for opposite things, which is a "
                     f"question about the ticket or the plan and not about the code. Read `review-{number}.json` and "
                     f"`review-{number + 1}.json`")
        return text

    # --------------------------------------------------------------- outcomes

    def _give_up(self, ticket: tk.Ticket, reason: str, detail: str) -> Outcome:
        """End a failed attempt: keep its evidence, put the tree back, say why."""
        work = ticket.work_dir(self.root)
        work.mkdir(parents=True, exist_ok=True)
        (work / "attempt-final.patch").write_text(git.patch_against(self.root, self.base) + "\n", encoding="utf-8")
        git.reset_to(self.root, self.base)
        files = sorted(path.name for path in work.iterdir() if path.name != "RESCUE.md")
        report.rescue(self.root, ticket, reason, detail, files, self.limits)
        return Outcome("blocked", reason, detail, stats=dict(self.stats))

    def record(self, ticket: tk.Ticket, outcome: Outcome) -> str:
        """Write an attempt's result into the repository: status, ledger, handoff, one commit.

        For a finished ticket the working tree must hold its change, which the commit takes along.
        """
        self.stats = dict(outcome.stats)
        if outcome.kind == "blocked":
            tk.set_status(ticket, "blocked", outcome.reason)
            report.ledger(self.root, ticket, f"blocked: {outcome.reason}", self.stats, outcome.detail)
            self._handoff(f"{ticket.id} is blocked ({outcome.reason}).", [])
            git.commit_all(self.root, f"{report.tag(ticket)} blocked: {outcome.reason}")
            self._state(ticket=ticket.id, step="blocked", reason=outcome.reason, **self.stats)
            _say(f"{ticket.id} BLOCKED ({outcome.reason}): {outcome.detail}")
            return "blocked"
        note = []
        if outcome.discarded:
            note.append("discarded out-of-scope: " + ", ".join(sorted(set(outcome.discarded))))
        if outcome.findings:
            note.append(f"{outcome.findings} minor finding(s) in review.json")
        note += outcome.notes
        tk.set_status(ticket, "done")
        for closed in features.close_finished(self.root):
            _say(f"{closed} is done: this was its last ticket")
        report.ledger(self.root, ticket, "done", self.stats, "; ".join(note))
        self._handoff(f"Last ticket finished: {ticket.id}.", [])
        commit = git.commit_all(self.root, f"{report.tag(ticket)} {ticket.title}")
        self._state(ticket=ticket.id, step="done", commit=commit, **self.stats)
        _say(f"{ticket.id} done ({commit[:8]})")
        return "done"

    def _infra(self, ticket: tk.Ticket, detail: str) -> None:
        """Stop without spending an attempt: save the work as a patch and restore the tree."""
        work = ticket.work_dir(self.root)
        work.mkdir(parents=True, exist_ok=True)
        if self.base:
            (work / "interrupted.patch").write_text(git.patch_against(self.root, self.base) + "\n", encoding="utf-8")
            git.reset_to(self.root, self.base)
        self._state(ticket=ticket.id, step="interrupted", reason=detail, **self.stats)
        raise Halt(EXIT_INFRA, f"{ticket.id} interrupted, nothing was lost or counted: {detail}")

    def _checked(self, ticket: tk.Ticket, result: adapters.Result) -> Optional[Outcome]:
        """Return a blocked outcome for an oversize call, halt on an infrastructure failure, else None."""
        if result.kind == adapters.OVERSIZE:
            return self._give_up(ticket, "oversize", result.detail + " — the ticket is too large for one session; split it")
        if result.kind == adapters.INFRA:
            self._infra(ticket, result.detail)
        return None

    # ---------------------------------------------------------------- a ticket

    def work(self, ticket: tk.Ticket) -> str:
        """Take one ticket to `done` or `blocked`, and record that."""
        return self.record(ticket, self.attempt(ticket))

    def attempt(self, ticket: tk.Ticket) -> Outcome:
        """Work one ticket in this tree without recording anything.

        A finished attempt leaves its change in the working tree (and as review.patch in
        the ticket's work folder); a blocked one leaves the tree as it was.
        """
        self.base = git.head(self.root)
        self.sequence = 0
        self.stats = {"cycles": 0, "reviews": 0, "verify_runs": 0, "max_tokens_in": 0, "tokens_in_total": 0}
        work = ticket.work_dir(self.root)
        work.mkdir(parents=True, exist_ok=True)
        relative = f"{tk.TICKET_DIR}/{tk.WORK_DIR}/{ticket.id}"
        discarded: List[str] = []
        notes: List[str] = []
        over = self._read_budget(ticket)
        if over:
            # Before any model call: the Engineer would start with more than the tier's window allows for reading.
            return self._give_up(ticket, "oversize", over)
        step, extra = "implement", ""
        rounds = 0
        first_review: Dict[str, Any] = {}
        while True:
            before = self._ticket_files(ticket)
            result = self._call("engineer", ticket, self._engineer_prompt(ticket, step, extra))
            blocked = self._checked(ticket, result)
            if blocked:
                return blocked
            rounds += 1
            # What the Engineer said is evidence: kept beside the logs, and read below when it reports a failure.
            said = result.text.strip()
            (work / "engineer-report.md").write_text((said or "(the Engineer's final message was empty)") + "\n", encoding="utf-8")
            self._keep_owner_notes(ticket, said)
            discarded += self._enforce_scope(ticket)
            failure = self.failure_report(said)
            if failure and self._ticket_files(ticket) == before:
                # The Engineer refused and this call changed none of the ticket's files: its reason is the finding,
                # in the first round and in any later one. A verify run and a Diagnostic would reach the same
                # verdict at the price of a run and a model call, and file it as a failed verify.
                who = "the Engineer" if rounds == 1 else f"in round {rounds} the Engineer"
                return self._give_up(ticket, "ticket-defect", (
                    f"{who} changed nothing and reported: {failure} — the ticket asks for something its files "
                    f"or the existing tests do not allow; the full report is `{relative}/engineer-report.md`"))
            code, tail = self._verify(ticket)
            discarded += self._enforce_scope(ticket, by="the verify command")
            if code != 0:
                # A machine fault is not the ticket's: put it back uncounted before any Diagnostic is paid for.
                problem = self._environment_problem()
                if problem:
                    self._infra(ticket, f"its verify exited {code} and {problem}")
                if self.stats["cycles"] >= int(self.limits["diagnostic_cycles"]):
                    return self._give_up(ticket, "verify", f"`{ticket.verify}` still exits {code} after "
                                                           f"{self.stats['cycles']} diagnostic cycle(s)")
                self.stats["cycles"] += 1
                patch = git.patch_against(self.root, self.base)
                number = self.stats["cycles"]
                (work / f"attempt-{number}.patch").write_text(patch + "\n", encoding="utf-8")
                prompt = "\n".join([f"TICKET {ticket.path.relative_to(self.root)}", "STEP diagnose",
                                    f"LOG {relative}/{tail.name}", f"DIFF {relative}/attempt-{number}.patch",
                                    *self._verify_lines(ticket)])
                result = self._read_only_call("diagnostic", ticket, prompt, patch)
                blocked = self._checked(ticket, result)
                if blocked:
                    return blocked
                diagnosis = "\n".join(result.text.strip().splitlines()[:DIAGNOSIS_MAX_LINES])
                if diagnosis.startswith("TICKET-DEFECT"):
                    return self._give_up(ticket, "ticket-defect", diagnosis.splitlines()[0])
                if not diagnosis:
                    diagnosis = "The diagnostic agent returned nothing. Work from the verify log directly."
                (work / "diagnosis.md").write_text(diagnosis + "\n", encoding="utf-8")
                step, extra = "fix", f"DIAGNOSIS {relative}/diagnosis.md\nLOG {relative}/{tail.name}"
                continue
            if failure:
                # Verify passes and the Engineer says it failed. The exit code decides against a model's claim of
                # success (D-04); a claim of failure is evidence the exit code cannot overrule. Seen in a pilot: a
                # timing test passed 4 of the Engineer's 12 runs, passed the runner's one, and the ticket closed.
                return self._give_up(ticket, "engineer-failed", (
                    f"verify exits 0, but the Engineer reported: {failure} — a pass its own Engineer does not stand "
                    f"behind closes nothing. Read `{relative}/engineer-report.md` and decide whether the ticket, the "
                    "test or the product is at fault"))
            failed, rewritten = True, []
            if ticket.red_check:
                if not any(git.differs_from(self.root, self.base, path) for path in ticket.writes):
                    # Nothing to remove, so the red check cannot fail, and no further Engineer round can change that.
                    return self._give_up(ticket, "ticket-defect", (
                        f"`{ticket.verify}` passes although the attempt left every `writes` file as it was at the "
                        f"commit before the ticket ({', '.join(ticket.writes)}). Either an earlier ticket already "
                        "holds this behaviour or the test does not test it, and the red check cannot tell which. If "
                        "the behaviour is already there, make the ticket test-only (`writes: []`, `red_check: false`) "
                        "or fold it into the ticket that wrote the file. The Engineer's own account is "
                        f"`{relative}/engineer-report.md`"))
                failed, rewritten = self._red_check(ticket, self._red_command(ticket, discarded, notes))
                discarded += self._enforce_scope(ticket, by="the verify command")
            if not failed and rewritten:
                return self._give_up(ticket, "ticket-defect", (
                    f"the verify command itself writes {', '.join(f'`{path}`' for path in rewritten)}, so removing "
                    "the file proves nothing: the red check cannot judge a file the build generates. Set "
                    "`red_check: false` on the ticket and say in it how the test was shown to fail"))
            if not failed:
                if self.stats["cycles"] >= int(self.limits["diagnostic_cycles"]):
                    return self._give_up(ticket, "red-check", "the tests still pass with the implementation removed")
                self.stats["cycles"] += 1
                (work / "diagnosis.md").write_text(
                    "The verify command passes even when the implementation file is put back to its state "
                    "before this ticket. The tests therefore do not test the ticket's behaviour.\n"
                    "Fix: make the test assert the behaviour in the ticket's Acceptance list through the public "
                    "interface, with expected values taken from the ticket, not recomputed by the code under test.\n",
                    encoding="utf-8")
                step, extra = "fix", f"DIAGNOSIS {relative}/diagnosis.md"
                continue
            patch = git.patch_against(self.root, self.base)
            (work / "review.patch").write_text(patch + "\n", encoding="utf-8")
            prompt = "\n".join([f"TICKET {ticket.path.relative_to(self.root)}", "STEP review",
                                f"DIFF {relative}/review.patch"])
            result = self._read_only_call("reviewer", ticket, prompt, patch)
            blocked = self._checked(ticket, result)
            if blocked:
                return blocked
            review = self.parse_review(result.text, patch)
            if review is None:
                # One more try for the reviewer alone; the code is not touched in between.
                result = self._read_only_call("reviewer", ticket, prompt + "\nREPLY with the JSON object only.", patch)
                blocked = self._checked(ticket, result)
                if blocked:
                    return blocked
                review = self.parse_review(result.text, patch)
                if review is None:
                    return self._give_up(ticket, "malformed", "the reviewer twice returned something that is not the review JSON")
            # Every round is kept; review.json is always the latest, which is what the Engineer reads.
            for name in (f"review-{self.stats['reviews'] + 1}.json", "review.json"):
                (work / name).write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
            if review["verdict"] == "PASS":
                return Outcome("done", discarded=discarded, findings=len(review["findings"]), notes=notes,
                               stats=dict(self.stats))
            if self.stats["reviews"] >= int(self.limits["review_retries"]):
                claims = "; ".join(str(finding.get("claim")) for finding in review["findings"][:3])
                return self._give_up(ticket, "review", f"the reviewer still requests changes: {claims}"
                                     + self._rounds_compared(first_review, review))
            if not first_review:
                # The index holds the tree the Reviewer has just read (patch_against staged it).
                first_review = {"tree": git.git(self.root, "write-tree"), "round": self.stats["reviews"] + 1,
                                "claims": "; ".join(str(finding.get("claim")) for finding in review["findings"][:3])}
            self.stats["reviews"] += 1
            step, extra = "revise", f"REVIEW {relative}/review.json"

    # ------------------------------------------------------------- the phase

    def _run_gate(self, seam: bool = True) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Run the gate commands this tree still owes. Returns (one result per command, files they wrote that no ticket owns).

        A command that is green on this tree is not run again: the same command on the same files
        can say nothing new (design D-32). `seam` says the build is being handed over, to the owner
        for an exit demo or to a merge: every `phase_gate` and `seam_gate` command the tree owes
        then runs. At an ordinary completion a `seam_gate` command runs only while it has never
        passed in this phase, which makes the first completion a seam too; after that it is left
        for the gate before the merge. The quick commands run first, and while one of them is not
        green the long ones do not run: the fix will change the tree and they would be owed again.

        A result is {command, kind, ran, code, stale, commit, seconds, log, owed, changed, since}.
        `stale` is the output line that shows a command reused an earlier result instead of
        running, or '': such a command proved nothing about the tree, whatever its exit status.
        `commit` is the commit the result was earned on. `owed` is '' when the result stands,
        'merge' for a long suite left for the merge, 'red' for one held back by a red quick command.
        """
        patterns = [re.compile(pattern) for pattern in
                    list(GATE_STALE) + [str(item) for item in self.config.get("phase_gate_stale") or []]]
        head = git.head(self.root)
        record = gates.read(self.root, self.phase)
        results: List[Dict[str, Any]] = []
        quick_red = False
        for index, (command, kind) in enumerate(gates.commands(self.config), start=1):
            log = self.root / tk.TICKET_DIR / tk.WORK_DIR / f"phase-{self.phase:02d}-gate-{index}.log"
            state = gates.state(self.root, self.config, command, record)
            result: Dict[str, Any] = {"command": command, "kind": kind, "ran": False, "code": 0, "stale": "",
                                      "commit": state["green_at"], "seconds": 0, "log": str(log.relative_to(self.root)),
                                      "owed": "", "changed": state["changed"], "since": state["since"]}
            results.append(result)
            if state["green_at"]:
                _say(f"phase gate: `{command}` is green on this tree (it passed on {state['green_at'][:8]}); not run again")
                continue
            if kind == gates.SEAM and not seam and state["ever"]:
                result["owed"] = "merge"
                _say(f"phase gate: `{command}` is left for the gate before the merge: {state['why']}")
                continue
            if kind == gates.SEAM and quick_red:
                result["owed"] = "red"
                _say(f"phase gate: `{command}` not run while a quick command is not green")
                continue
            _say(f"phase gate: {command}")
            self._state(step="gate", command=command, done=[f"{gate['command']}: exit {gate['code']}" for gate in results[:-1]
                                                             if gate["ran"]])
            started = time.time()
            code = self._shell(command, log)
            printed = log.read_text(encoding="utf-8", errors="replace").splitlines()[1:]    # line 1 is the command itself
            stale = next((line.strip() for line in printed if any(pattern.search(line) for pattern in patterns)), "")
            if stale:
                _say(f"phase gate: `{command}` reused an earlier result and ran no test: {stale}")
            result.update(ran=True, code=code, stale=stale, commit=head, seconds=int(round(time.time() - started)))
            # Recorded and said as each command ends: a gate can run for half an hour, and until this was
            # so, nobody could tell which of its commands had already passed without reading build logs.
            gates.append(self.root, self.phase, report.now(), head, command, code, stale, result["seconds"], result["log"])
            how = f"red (exit {code})" if code != 0 else "did not run" if stale else "green"
            _say(f"phase gate: `{command}` {how} in {result['seconds']} s")
            if kind == gates.QUICK and (code != 0 or stale):
                quick_red = True
        # The tree was clean before the gate ran, so whatever differs now the gate wrote, its own
        # record apart. No ticket owns it and nobody reviewed it: it does not ride along in the closing commit.
        stray = self._outside({gates.record_name(self.phase)})
        if stray:
            git.restore_paths(self.root, git.head(self.root), stray)
            _say(f"phase gate: discarded files no ticket owns: {', '.join(stray)}")
        return results, stray

    @staticmethod
    def _gate_verdict(results: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """('' when green, else what is wrong in a few words; the owner's steps for it).

        A long suite left for the merge is not wrong: the caller reports it as owed.
        """
        failed = [f"`{gate['command']}`" for gate in results if gate["ran"] and gate["code"] != 0]
        stale = [gate for gate in results if gate["ran"] and gate["code"] == 0 and gate["stale"]]
        held = [f"`{gate['command']}`" for gate in results if gate["owed"] == "red"]
        parts, steps = [], []
        if failed:
            parts.append("is red: " + ", ".join(failed))
            steps += ["Read the gate logs in `.tickets/.work/`.", "Fix the cause as a new ticket in this phase, then run again."]
        if stale:
            parts.append("did not run: " + ", ".join(f"`{gate['command']}` reused an earlier result (`{gate['stale']}`)"
                                                     for gate in stale))
            steps.append("Make every `phase_gate` and `seam_gate` command in `.devpipe/config.json` run its tests each "
                         "time (for Gradle, add `--rerun-tasks`), then run again: a gate that reuses results cannot show "
                         "a test that fails only sometimes, or a check whose inputs the build does not know about.")
        if held:
            steps.append(f"{', '.join(held)} {'was' if len(held) == 1 else 'were'} not run while a quick command is not "
                         "green: the fix changes the tree, and the long suites run on the tree that has it.")
        return " and ".join(parts), steps

    def _stray_step(self, stray: List[str]) -> List[str]:
        if not stray:
            return []
        shown = ", ".join(f"`{path}`" for path in stray[:8]) + (f" and {len(stray) - 8} more" if len(stray) > 8 else "")
        return [f"The phase gate wrote files that no ticket owns, and they were discarded: {shown}. If the "
                "repository must keep one, name it under a ticket's `writes` or add its pattern to "
                "`scope_allow` in `.devpipe/config.json`; otherwise add it to `.gitignore`."]

    def _merge_step(self, results: List[Dict[str, Any]]) -> str:
        """The owner's last step after a green completion: the gate before the merge, then the merge."""
        branch = f"phase/{self.phase:02d}"
        if not results:
            return f"Merge `{branch}` yourself when both are closed."
        owed = [f"`{gate['command']}`" for gate in results if gate["owed"] == "merge"]
        will = (f" It will run {', '.join(owed)}." if owed
                else " It runs only what the tree has not passed by then, which may be nothing.")
        return (f"When both are closed, run `devpipe gate --phase {self.phase}` and merge `{branch}` yourself once it "
                f"is green.{will}")

    def _finish_phase(self) -> int:
        results, stray = self._run_gate(seam=False)
        wrong, steps = self._gate_verdict(results)
        brief = report.review_brief(self.root, self.phase, results)
        if wrong:
            headline = f"All tickets are done, but the phase gate {wrong}."
        else:
            headline = "All tickets are done and the phase gate is green."
            owed = sum(1 for gate in results if gate["owed"] == "merge")
            if owed:
                headline += f" {owed} long suite{' is' if owed == 1 else 's are'} owed before the merge."
            steps = [f"Run your reviewer on `{brief.relative_to(self.root)}` with a different model.",
                     "Do the handoff check: README, then RUNBOOK, then TESTING only.",
                     self._merge_step(results)]
        self._handoff(headline, steps + self._stray_step(stray))
        if not git.is_clean(self.root):
            git.commit_all(self.root, f"[P{self.phase:02d}] phase {'gate not green' if wrong else 'complete'}: review brief")
        _say(headline)
        return EXIT_OWNER if wrong else EXIT_DONE

    def merge_gate(self) -> int:
        """The gate before the merge (`devpipe gate`): run every gate command this tree has not passed.

        The runner never merges, so this is the owner's last step before they do, and the one
        place a long suite runs after the phase's first review. A tree that has passed everything
        costs nothing here. Returns the exit status: 0 only when every command is green on this tree.
        """
        results, stray = self._run_gate(seam=True)
        if not any(gate["ran"] for gate in results):
            _say("the gate before the merge has nothing to run: "
                 + ("every gate command is green on this tree" if results
                    else "no gate command is configured in .devpipe/config.json"))
            return EXIT_DONE
        wrong, steps = self._gate_verdict(results)
        if wrong:
            headline = f"The gate before the merge {wrong}."
        else:
            headline = "The gate before the merge is green: every gate command has passed on this tree."
            steps = [f"Merge `phase/{self.phase:02d}` yourself."]
        self._handoff(headline, steps + self._stray_step(stray), gate_ran=True)
        if not git.is_clean(self.root):
            git.commit_all(self.root, f"[P{self.phase:02d}] gate before the merge: {'not green' if wrong else 'green'}")
        _say(headline)
        return EXIT_OWNER if wrong else EXIT_DONE

    def _is_manual(self, ticket: tk.Ticket) -> bool:
        return ticket.mode == "hitl" or ticket.host not in ("any", self.host)

    def _manual_stop(self, ticket: tk.Ticket, in_phase: List[tk.Ticket]) -> Halt:
        """Hand a manual ticket to the owner: handoff, one commit, and the Halt to raise.

        When nothing but manual tickets is left, the phase gate runs first, long suites
        included. The owner's manual step at the end of a phase is usually its exit demo, and
        a demo performed on a build the whole-repository checks have never passed may have to
        be done twice.
        """
        why = "is a manual ticket" if ticket.mode == "hitl" else f"must run on a {ticket.host} machine"
        headline, first = f"{ticket.id} {why}.", []
        only_manual = all(self._is_manual(other) for other in in_phase if other.status != "done")
        gated = only_manual and bool(gates.commands(self.config))
        if gated:
            # Handing the build to the owner is a seam: the long suites run here too, unless this
            # tree has passed them already.
            results, stray = self._run_gate(seam=True)
            wrong, steps = self._gate_verdict(results)
            if wrong or any(gate["ran"] for gate in results):
                headline += f" The phase gate was run first and {wrong or 'is green'}."
            else:
                headline += " The phase gate is green on this tree: nothing a gate reads has changed since it passed."
            if wrong:
                first = [f"Before the manual ticket, the phase gate {wrong}."] + steps
            first += self._stray_step(stray)
        self._handoff(headline, first + [f"Do `{ticket.path.relative_to(self.root)}` yourself.",
                                         f"Then run `devpipe ticket done {ticket.id}` and start the phase again."],
                      gate_ran=gated)
        if not git.is_clean(self.root):
            git.commit_all(self.root, f"[P{self.phase:02d}] stopped: {ticket.id} needs the owner")
        _say(headline)
        return Halt(EXIT_OWNER, f"{headline} See HANDOFF.md")

    def _nothing_ready(self, in_phase: List[tk.Ticket]) -> Halt:
        """Stop because no ticket can start: handoff, one commit, and the Halt to raise.

        Every run that does not finish the phase ends here or in `_manual_stop`. When all that
        is left is manual, this is a manual handover, with the gate first, however the run got
        here: a run that continues past blocks skips manual tickets on its way and must not
        skip the gate with them.
        """
        unfinished = [ticket for ticket in in_phase if ticket.status != "done"]
        manual = [ticket for ticket in unfinished if ticket.status == "todo" and self._is_manual(ticket)]
        if unfinished and len(manual) == len(unfinished):
            status = {ticket.id: ticket.status for ticket in tk.load_all(self.root)}
            startable = [ticket for ticket in manual if all(status.get(blocker) == "done" for blocker in ticket.blocked_by)]
            return self._manual_stop((startable or manual)[0], in_phase)
        blocked = [ticket.id for ticket in unfinished if ticket.status == "blocked"]
        waiting = len(unfinished) - len(blocked) - len(manual)
        parts = []
        if blocked:
            parts.append(", ".join(blocked) + " blocked")
        if manual:
            parts.append(", ".join(ticket.id for ticket in manual) + " manual and left for you")
        if waiting:
            parts.append(f"{waiting} waiting on {'them' if blocked or manual else 'tickets that are not done'}")
        headline = "No ticket is ready: " + "; ".join(parts) + "."
        self._handoff(headline, self._waiting_steps(bool(blocked), bool(manual)))
        if not git.is_clean(self.root):
            git.commit_all(self.root, f"[P{self.phase:02d}] stopped: handoff updated")
        return Halt(EXIT_OWNER, headline)

    @staticmethod
    def _waiting_steps(blocked: bool, manual: bool) -> List[str]:
        """Owner's steps when nothing is ready; the handoff adds one per blocked ticket itself."""
        steps = []
        if manual:
            steps.append("Do the manual tickets listed under Next yourself, then `devpipe ticket done <id>` for each.")
        if not blocked and not manual:
            steps.append("The remaining tickets wait for tickets that are not done; `devpipe status` shows which.")
        return steps

    def run(self) -> int:
        """Run the phase until it completes or needs the owner. Returns the exit status."""
        self.preflight()
        finished = 0
        skipped: Set[str] = set()
        while True:
            if self._pause_file().exists():
                # Between tickets the tree is clean and committed, which is the only moment a
                # stage may change the specification, the plan or the tickets.
                self._pause_file().unlink(missing_ok=True)
                raise Halt(EXIT_DONE, f"paused as asked after {finished} ticket(s); "
                                      f"`devpipe run --phase {self.phase}` continues")
            everything = tk.load_all(self.root)
            in_phase = [ticket for ticket in everything if ticket.phase == self.phase]
            if all(ticket.status == "done" for ticket in in_phase):
                return self._finish_phase()
            ready = [ticket for ticket in tk.frontier(in_phase, everything) if ticket.id not in skipped]
            if not ready:
                raise self._nothing_ready(in_phase)
            ticket = ready[0]
            if self._is_manual(ticket):
                if self.continue_on_block:
                    skipped.add(ticket.id)
                    _say(f"{ticket.id} is left for the owner; skipped")
                    continue
                raise self._manual_stop(ticket, in_phase)
            try:
                outcome = self.work(ticket)
            except KeyboardInterrupt:
                self._infra(ticket, "interrupted from the keyboard")
            finished += 1
            if outcome == "blocked" and not self.continue_on_block:
                raise Halt(EXIT_OWNER, f"{ticket.id} is blocked; see .tickets/.work/{ticket.id}/RESCUE.md")
            if self.max_tickets and finished >= self.max_tickets:
                raise Halt(EXIT_DONE, f"stopped after {finished} ticket(s) as asked")
