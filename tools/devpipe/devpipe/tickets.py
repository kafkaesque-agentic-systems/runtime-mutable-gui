"""Ticket files (`.tickets/phase-NN/ticket-NN.md`).

Purpose: load tickets, compute the frontier and change a ticket's status. The
ticket's `status:` line is the durable record of progress; the runner state
file is only a scratch note beside it.
Side effects: `set_status` rewrites one line of one ticket file.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from . import fm

TICKET_DIR = ".tickets"
WORK_DIR = ".work"
# At least two digits each. The ticket number may be written with up to four (T100 follows
# T99, or a large phase uses T001 throughout); the file name carries the same digits.
ID_PATTERN = re.compile(r"^P(\d{2,3})-T(\d{2,4})$")
STATUSES = ("todo", "done", "blocked")
MODES = ("afk", "hitl")
HOSTS = ("any", "linux", "mac")


class TicketError(ValueError):
    """A ticket file cannot be read as a ticket."""


@dataclass
class Ticket:
    """One ticket; `meta` keeps the raw header for the lint."""

    path: Path
    meta: Dict[str, Any]
    body: str
    id: str = ""
    phase: int = 0
    number: int = 0
    title: str = ""
    status: str = "todo"
    mode: str = "afk"
    host: str = "any"
    blocked_by: List[str] = field(default_factory=list)
    read: List[Dict[str, Any]] = field(default_factory=list)
    writes: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    verify: str = ""
    red_check: bool = False
    # A narrower command for the red check: the ticket's own tests only (design D-32).
    red_verify: str = ""
    # True: in a parallel run nothing else is in progress while this ticket is (design D-34).
    alone: bool = False

    @property
    def tag(self) -> str:
        """Commit-message tag, the id as written: `P02-T107` gives `[P02.T107]`."""
        return "[" + self.id.replace("-", ".") + "]"

    @property
    def file_name(self) -> str:
        """Where the ticket belongs under `.tickets/`, from the id as written."""
        match = ID_PATTERN.match(self.id)
        return f"phase-{match.group(1)}/ticket-{match.group(2)}.md" if match else ""

    def work_dir(self, root: Path) -> Path:
        """Folder for this ticket's logs, patches and agent outputs (gitignored)."""
        return root / TICKET_DIR / WORK_DIR / self.id


def _strings(value: Any) -> List[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def load(path: Path) -> Ticket:
    """Read one ticket. Raises TicketError when the header or id is unusable."""
    try:
        meta, body = fm.load(path.read_text(encoding="utf-8"))
    except (OSError, fm.FrontMatterError) as error:
        raise TicketError(f"{path}: {error}") from error
    ticket_id = str(meta.get("id", ""))
    match = ID_PATTERN.match(ticket_id)
    if not match:
        raise TicketError(f"{path}: id {ticket_id!r} does not look like P02-T07 (or P02-T107, P02-T0107)")
    if match.group(1) != f"{int(match.group(1)):02d}":
        raise TicketError(f"{path}: the phase in {ticket_id!r} is written P{int(match.group(1)):02d}, without extra zeros")
    read = [entry if isinstance(entry, dict) else {"path": str(entry)}
            for entry in meta.get("read", []) if entry != ""] if isinstance(meta.get("read"), list) else []
    return Ticket(
        path=path, meta=meta, body=body, id=ticket_id,
        phase=int(match.group(1)), number=int(match.group(2)),
        title=str(meta.get("title", "")), status=str(meta.get("status", "todo")),
        mode=str(meta.get("mode", "afk")), host=str(meta.get("host", "any")),
        blocked_by=_strings(meta.get("blocked_by")), read=read,
        writes=_strings(meta.get("writes")), tests=_strings(meta.get("tests")),
        verify=str(meta.get("verify", "")), red_check=meta.get("red_check") is True,
        red_verify=str(meta.get("red_verify") or ""), alone=meta.get("alone") is True,
    )


def phase_dir(root: Path, phase: int) -> Path:
    return root / TICKET_DIR / f"phase-{phase:02d}"


def load_phase(root: Path, phase: int) -> List[Ticket]:
    """Tickets of one phase in number order."""
    folder = phase_dir(root, phase)
    found = [load(path) for path in sorted(folder.glob("ticket-*.md"))]
    return sorted(found, key=lambda ticket: ticket.number)


def load_all(root: Path) -> List[Ticket]:
    """Every ticket in the repository, phase then number."""
    found = [load(path) for path in sorted((root / TICKET_DIR).glob("phase-*/ticket-*.md"))]
    return sorted(found, key=lambda ticket: (ticket.phase, ticket.number))


def frontier(phase_tickets: List[Ticket], everything: List[Ticket]) -> List[Ticket]:
    """Tickets that are `todo` and whose blockers are all `done`, in number order."""
    status = {ticket.id: ticket.status for ticket in everything}
    return [ticket for ticket in phase_tickets
            if ticket.status == "todo"
            and all(status.get(blocker) == "done" for blocker in ticket.blocked_by)]


def set_status(ticket: Ticket, status: str, reason: str = "") -> None:
    """Persist a new status (and the reason for a block) in the ticket file."""
    if status not in STATUSES:
        raise TicketError(f"unknown status {status!r}")
    text = fm.set_scalar(ticket.path.read_text(encoding="utf-8"), "status", status)
    if reason:
        text = fm.set_scalar(text, "blocked_reason", '"' + reason.replace('"', "'") + '"')
    ticket.path.write_text(text, encoding="utf-8")
    ticket.status = status
