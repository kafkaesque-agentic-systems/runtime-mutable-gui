"""Parallel phase runs (`devpipe run --phase N --jobs K`).

Purpose: finish a phase in less wall time by working tickets that share no file
at the same time. Each attempt runs in its own git worktree as a separate
`devpipe worker` process; this coordinator stays in the project folder, picks
what may start, and records every result on the phase branch itself, one
ticket and one commit at a time, exactly as the serial runner does.
Dependencies: runner (the attempt and the record), features (which files a
ticket uses), gitutil, tickets, report.
Side effects: creates and resets worktrees outside the project folder, starts
worker processes, applies finished patches to the project's working tree and
commits them. Never pushes, pulls or merges.
"""
from __future__ import annotations

import fnmatch
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from . import features, gitutil as git, report, runner, tickets as tk
from .runner import EXIT_DONE, EXIT_INFRA, EXIT_OWNER, Halt, Outcome, _say

POLL_SECONDS = 0.5
OUTCOME_FILE = "outcome.json"
STOP_WAIT_SECONDS = 60


@dataclass
class Worker:
    """One attempt in progress."""

    ticket_id: str
    slot: int
    base: str                     # the phase branch's commit the attempt started from
    process: "subprocess.Popen[bytes]"
    paths: Dict[str, str]         # {file: 'writes' | 'reads'} of the ticket
    exclusive: bool
    alone: bool = False           # the ticket's `alone: true`: nothing starts while it is in progress


class ParallelRunner(runner.Runner):
    """Runs one phase with up to `jobs` tickets in progress. Create, then call `run()`."""

    def __init__(self, root: Path, phase: int, jobs: int, continue_on_block: bool = False, max_tickets: int = 0):
        super().__init__(root, phase, continue_on_block, max_tickets)
        self.jobs = jobs
        self.settings: Dict[str, Any] = self.config.get("parallel") or {}
        self.running: Dict[str, Worker] = {}
        self.returned: Dict[str, int] = {}   # how often a ticket went back in the queue

    # -------------------------------------------------------------- preflight

    def preflight(self) -> None:
        if self.adapter.name == "opencode":
            raise Halt(EXIT_OWNER, "--jobs needs the claude adapter: the opencode adapter talks to one local "
                                   "model, which serves one call at a time")
        super().preflight()

    # --------------------------------------------------------------- worktrees

    def worktree_dir(self) -> Path:
        configured = str(self.settings.get("worktree_dir") or "")
        if configured:
            return Path(configured).expanduser()
        # Outside the project, so no build or search tool in the project walks into them.
        return self.root.parent / ".devpipe-worktrees" / self.root.name

    def _prepare(self, slot: int, head: str, ticket: tk.Ticket) -> Path:
        """Make worktree `slot` a clean checkout of `head`, ready for `ticket`.

        A slot is reused from ticket to ticket, so ignored build output stays warm.
        """
        path = self.worktree_dir() / f"worker-{slot}"
        if path.exists():
            if not git.is_worktree_of(self.root, path):
                raise Halt(EXIT_OWNER, f"{path} exists and is not a worktree of this repository; remove it "
                                       "or set parallel.worktree_dir in .devpipe/config.json")
            git.git(path, "reset", "-q", "--hard")
            git.git(path, "clean", "-q", "-fd")
            git.git(path, "checkout", "-q", "--detach", head)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            git.git(self.root, "worktree", "prune")
            git.git(self.root, "worktree", "add", "-q", "--detach", str(path), head)
        for name in self.settings.get("copy") or []:
            source, target = self.root / str(name), path / str(name)
            if source.is_file() and (not target.is_file() or target.read_bytes() != source.read_bytes()):
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        # The ticket's work folder is the project's own, reached through a link, so prompts can
        # name it by the same relative path and its logs end up where `status` and the owner look.
        shared = ticket.work_dir(self.root)
        shared.mkdir(parents=True, exist_ok=True)
        (shared / OUTCOME_FILE).unlink(missing_ok=True)
        link = ticket.work_dir(path)
        link.parent.mkdir(parents=True, exist_ok=True)
        if link.is_symlink():
            link.unlink()
        elif link.exists():
            shutil.rmtree(link)
        link.symlink_to(shared, target_is_directory=True)
        return path

    # ------------------------------------------------------------- scheduling

    def _exclusive(self, ticket: tk.Ticket) -> bool:
        return any(fnmatch.fnmatch(ticket.verify, str(pattern)) for pattern in self.settings.get("exclusive") or [])

    def _manual(self, ticket: tk.Ticket) -> bool:
        return self._is_manual(ticket)

    def compatible(self, ticket: tk.Ticket) -> bool:
        """True when `ticket` may run beside everything in progress.

        Two tickets never run together when one writes a file the other reads or writes,
        or when both need the one resource the `exclusive` patterns stand for.
        """
        if self.running and (ticket.alone or any(worker.alone for worker in self.running.values())):
            # A ticket that measures the machine (a timing bound) or needs all of it runs with nothing beside it.
            return False
        mine = features.used_paths(ticket)
        for worker in self.running.values():
            if worker.exclusive and self._exclusive(ticket):
                return False
            for path, how in mine.items():
                other = worker.paths.get(path)
                if other and "writes" in (how, other):
                    return False
        return True

    def _launch(self, ticket: tk.Ticket) -> None:
        slot = min(set(range(1, self.jobs + 1)) - {worker.slot for worker in self.running.values()})
        head = git.head(self.root)
        path = self._prepare(slot, head, ticket)
        command = [sys.executable, str(Path(__file__).resolve().parent.parent / "run.py"), "worker",
                   "--phase", str(self.phase), "--ticket", ticket.id]
        # The worker shares this process's output, so the run log shows every ticket's steps.
        process = subprocess.Popen(command, cwd=str(path), stdin=subprocess.DEVNULL)
        self.running[ticket.id] = Worker(ticket.id, slot, head, process, features.used_paths(ticket),
                                         self._exclusive(ticket), ticket.alone)
        _say(f"{ticket.id} started in worker-{slot} at {head[:8]}")

    def _stop_workers(self) -> None:
        """End every attempt in progress; each worker puts its own worktree back."""
        for worker in self.running.values():
            if worker.process.poll() is None:
                worker.process.terminate()
        deadline = time.time() + STOP_WAIT_SECONDS
        for worker in self.running.values():
            try:
                worker.process.wait(timeout=max(deadline - time.time(), 0.1))
            except subprocess.TimeoutExpired:
                worker.process.kill()
        self.running.clear()

    # ------------------------------------------------------------ integration

    def _ticket(self, ticket_id: str) -> tk.Ticket:
        return next(ticket for ticket in tk.load_all(self.root) if ticket.id == ticket_id)

    def _integrate(self, worker: Worker, code: int) -> Tuple[str, str]:
        """Record a finished attempt on the phase branch.

        Returns (result, detail): result is done, blocked, returned (back in the queue)
        or infra (the attempt was interrupted; nothing is counted).
        """
        ticket = self._ticket(worker.ticket_id)
        work = ticket.work_dir(self.root)
        try:
            data = json.loads((work / OUTCOME_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {"kind": "infra", "detail": f"its worker ended with status {code} and left no result"}
        if data.get("kind") == "infra":
            return "infra", str(data.get("detail", ""))
        outcome = Outcome(kind=str(data["kind"]), reason=str(data.get("reason", "")), detail=str(data.get("detail", "")),
                          discarded=[str(path) for path in data.get("discarded", [])],
                          findings=int(data.get("findings", 0)), notes=[str(note) for note in data.get("notes", [])],
                          stats=dict(data.get("stats", {})))
        head = git.head(self.root)
        self.base = head
        if outcome.kind == "blocked":
            return self.record(ticket, outcome), ""

        problem = ""
        patch = work / "review.patch"
        try:
            if patch.is_file() and patch.read_text(encoding="utf-8", errors="replace").strip():
                git.git(self.root, "apply", "--index", "--whitespace=nowarn", str(patch))
        except git.GitError as error:
            problem = f"its change does not apply on top of the tickets finished meanwhile ({str(error)[-160:]})"
        if not problem and head != worker.base and self.settings.get("reverify", True):
            # The attempt was verified without the tickets that landed while it ran.
            status = self._shell(ticket.verify, work / "90-integration-verify.log")
            _say(f"{ticket.id} verify exit {status} on the phase branch, with the tickets finished meanwhile")
            # This run of verify wrote its build output here, in the project folder.
            outcome.discarded += self._enforce_scope(ticket, by="the verify command")
            if status != 0:
                problem = f"`{ticket.verify}` exits {status} once the tickets finished meanwhile are in"
        if not problem:
            return self.record(ticket, outcome), ""

        git.reset_to(self.root, head)
        self.returned[ticket.id] = self.returned.get(ticket.id, 0) + 1
        if self.returned[ticket.id] > int(self.settings.get("integration_retries", 1)):
            files = sorted(path.name for path in work.iterdir() if path.name != "RESCUE.md")
            report.rescue(self.root, ticket, "integration", problem, files, self.limits)
            return self.record(ticket, Outcome("blocked", "integration", problem, stats=outcome.stats)), ""
        _say(f"{ticket.id} goes back in the queue: {problem}")
        return "returned", ""

    # -------------------------------------------------------------- the phase

    def run(self) -> int:
        """Run the phase until it completes or needs the owner. Returns the exit status."""
        self.preflight()
        _say(f"up to {self.jobs} tickets at a time; worktrees in {self.worktree_dir()}")
        finished = 0
        skipped: Set[str] = set()
        stopping: List[Halt] = []      # once set, nothing new starts; the run ends when the workers have
        try:
            while True:
                for worker in [worker for worker in self.running.values() if worker.process.poll() is not None]:
                    del self.running[worker.ticket_id]
                    result, detail = self._integrate(worker, int(worker.process.returncode))
                    if result in ("done", "blocked"):
                        finished += 1
                    if result == "infra":
                        stopping.insert(0, Halt(EXIT_INFRA, f"{worker.ticket_id} interrupted, nothing was lost "
                                                            f"or counted: {detail}"))
                    elif result == "blocked" and not self.continue_on_block:
                        stopping.append(Halt(EXIT_OWNER, f"{worker.ticket_id} is blocked; see "
                                                         f".tickets/.work/{worker.ticket_id}/RESCUE.md"))
                    elif self.max_tickets and finished >= self.max_tickets:
                        stopping.append(Halt(EXIT_DONE, f"stopped after {finished} ticket(s) as asked"))
                if not stopping and self._pause_file().exists():
                    self._pause_file().unlink(missing_ok=True)
                    stopping.append(Halt(EXIT_DONE, f"paused as asked after {finished} ticket(s); "
                                                    f"`devpipe run --phase {self.phase}` continues"))
                if stopping:
                    if not self.running:
                        raise stopping[0]
                    time.sleep(POLL_SECONDS)
                    continue

                everything = tk.load_all(self.root)
                in_phase = [ticket for ticket in everything if ticket.phase == self.phase]
                if all(ticket.status == "done" for ticket in in_phase):
                    return self._finish_phase()
                ready = [ticket for ticket in tk.frontier(in_phase, everything)
                         if ticket.id not in self.running and ticket.id not in skipped]
                # A ready ticket that must run alone is next: nothing else starts, so the tickets in
                # progress drain and it gets the machine. Otherwise it could wait for ever.
                holding = any(ticket.alone and not self._manual(ticket) for ticket in ready)
                for ticket in ready:
                    room = len(self.running) < self.jobs and \
                        not (self.max_tickets and finished + len(self.running) >= self.max_tickets)
                    if holding and not ticket.alone:
                        continue
                    if room and not self._manual(ticket) and self.compatible(ticket):
                        self._launch(ticket)
                if self.running:
                    self._state(jobs=self.jobs, running=sorted(self.running))
                    time.sleep(POLL_SECONDS)
                    continue

                # Nothing is in progress and nothing could start: the owner is needed.
                manual = [ticket for ticket in ready if self._manual(ticket)]
                if manual and not self.continue_on_block:
                    raise self._manual_stop(manual[0], in_phase)
                raise self._nothing_ready(in_phase)
        except KeyboardInterrupt:
            count = len(self.running)
            self._stop_workers()
            # An interrupt can land between applying a patch and committing it.
            git.reset_to(self.root, git.head(self.root))
            raise Halt(EXIT_INFRA, f"stopped; {count} ticket(s) in progress were put back and not counted")
        finally:
            if self.running:
                self._stop_workers()
