"""Runner-written records: ledger, HANDOFF.md, rescue packets, review briefs.

Purpose: every durable note about a run is produced here by code, not by a
model, so its size and shape are fixed. Agents are never told to read the
ledger, which is why it can grow without costing anyone context.
Side effects: writes the files named in each function.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import re

from . import features, gates, gitutil as git, lint, tickets as tk, tokens, ui

LEDGER_HEADER = ("# Ledger: phase {phase:02d}\n\n"
                 "One line per ticket event, appended by `devpipe run`. The commit for a ticket is the one\n"
                 "whose message starts with its tag, for example `git log --grep '\\[P02.T07\\]'`.\n\n"
                 "Largest prompt: the largest single request the tool reported for any agent call on the ticket, which\n"
                 "is what a window has to hold (0 when it reported none; with the claude adapter it is each call's last\n"
                 "request). Input, all calls: every request of every call added up, cache reads included, which is\n"
                 "what the ticket cost to read.\n\n"
                 "| When | Ticket | Result | Verify runs | Diagnostic cycles | Review rounds | Largest prompt (tokens) | "
                 "Input, all calls (tokens) | Note |\n"
                 "|---|---|---|---|---|---|---|---|---|\n")
TOTAL_COLUMN = "Input, all calls (tokens)"


def now() -> str:
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")


def tag(ticket: tk.Ticket) -> str:
    """Commit-message tag of a ticket: `[P02.T07]`."""
    return ticket.tag


def ledger_path(root: Path, phase: int) -> Path:
    return root / "docs" / "ledger" / f"phase-{phase:02d}.md"


def ledger(root: Path, ticket: tk.Ticket, result: str, stats: Dict[str, Any], note: str = "") -> None:
    """Append one row to the phase ledger, creating the file with its header."""
    path = ledger_path(root, ticket.phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(LEDGER_HEADER.format(phase=ticket.phase), encoding="utf-8")
    # A ledger an older toolkit started has no column for the total; its rows keep that shape.
    total = f" {stats.get('tokens_in_total', 0)} |" if TOTAL_COLUMN in path.read_text(encoding="utf-8") else ""
    row = "| {when} | {id} | {result} | {verify} | {cycles} | {reviews} | {tokens} |{total} {note} |\n".format(
        when=now(), id=ticket.id, result=result, verify=stats.get("verify_runs", 0),
        cycles=stats.get("cycles", 0), reviews=stats.get("reviews", 0),
        tokens=stats.get("max_tokens_in", 0), total=total, note=ledger_note(note))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(row)


LEDGER_NOTE_CHARS = 160


def ledger_note(note: str) -> str:
    """The note as one table cell: no pipe or newline, and a long note cut at a word boundary, ending in `…`."""
    text = note.replace("|", "/").replace("\n", " ").strip()
    if len(text) <= LEDGER_NOTE_CHARS:
        return text
    cut = text[:LEDGER_NOTE_CHARS - 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(" ,;:") + "…"


BLOCKED_SHOWN = 10
BUDGETS_SHOWN = 5
LOOP_SHOWN = 12
LOOP_NOTE_CHARS = 220


def cut(text: str, limit: int) -> str:
    """One line of at most `limit` characters, cut at a word and ending in `…` when it was longer."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    head = text[:limit - 1]
    space = head.rfind(" ")
    return (head[:space] if space > 0 else head).rstrip(" ,;:") + "…"


def handoff(root: Path, config: Dict[str, Any], phase: int, headline: str, owner_steps: List[str],
            counter: Optional[tokens.Counter] = None, gate_ran: bool = False) -> None:
    """Regenerate HANDOFF.md: fixed sections, bounded length.

    `owner_steps` is what this stop asks of the owner. One step per blocked ticket is added
    here, whoever calls and for whatever reason: a ticket that finishes after another has
    blocked rewrites this file, and the block is still the owner's to clear.
    """
    everything = tk.load_all(root)
    in_phase = [ticket for ticket in everything if ticket.phase == phase]
    done = [ticket for ticket in in_phase if ticket.status == "done"]
    blocked = [ticket for ticket in in_phase if ticket.status == "blocked"]
    ready = tk.frontier(in_phase, everything)
    lines = [
        "# Handoff", "",
        f"Updated {now()} by `devpipe run`. This file is regenerated at every stop; do not edit it.", "",
        "## State", "",
        f"- Phase {phase:02d}: {len(done)} of {len(in_phase)} tickets done, {len(blocked)} blocked.",
        f"- {headline}",
    ]
    if len(done) < len(in_phase):
        # Said at every stop, by whatever path it was reached: counts of done tickets read like
        # success, and a phase is complete only when its gate has run and its brief is written.
        lines.append(f"- The phase is not complete: {len(in_phase) - len(done)} of {len(in_phase)} tickets are unfinished, so "
                     + ("its review brief is not written yet." if gate_ran
                        else "the phase gate has not run and there is no review brief."))
    lines += [f"- Branch `phase/{phase:02d}`; nothing is pushed or merged by the runner.", "",
              "## Next", ""]
    lines += [f"- `{ticket.id}` {ticket.title} ({ticket.mode}, host {ticket.host})" for ticket in ready[:5]] or ["- No ticket is ready."]
    lines += ["", "## Blocked", ""]
    lines += [f"- `{ticket.id}` {ticket.title}: {ticket.meta.get('blocked_reason', 'see its work folder')}; "
              f"rescue packet `.tickets/.work/{ticket.id}/RESCUE.md`" for ticket in blocked[:BLOCKED_SHOWN]] or ["- None."]
    steps = list(owner_steps)
    steps += [f"`{ticket.id}` is blocked ({ticket.meta.get('blocked_reason', 'no reason recorded')}): read "
              f"`.tickets/.work/{ticket.id}/RESCUE.md`, fix the ticket or split it, and set its `status: todo`."
              for ticket in blocked[:BLOCKED_SHOWN]]
    if len(blocked) > BLOCKED_SHOWN:
        steps.append(f"{len(blocked) - BLOCKED_SHOWN} more tickets are blocked; `devpipe status` lists them all.")
    if blocked:
        steps.append(f"Then run the phase again: `devpipe run --phase {phase}`.")
    # Tickets still to run whose read manifest is over the limit, or close to it, as the files are now.
    heavy = [row for row in lint.read_report(root, config, phase, counter) if row["state"] != "ok"]
    over = [row["id"] for row in heavy if row["state"] == "over" and row["status"] == "todo"]
    if over:
        steps.append(f"{', '.join(over[:BUDGETS_SHOWN])}{' and more' if len(over) > BUDGETS_SHOWN else ''}: the read "
                     "manifest is over its limit, so the ticket blocks when it starts. Narrow its `read:` entries "
                     "first; `devpipe reads` shows what to narrow.")
    lines += ["", "## For the owner", ""]
    lines += [f"{index}. {step}" for index, step in enumerate(steps, start=1)] or ["Nothing is waiting on you."]
    if heavy:
        lines += ["", "## Read budgets", ""]
        lines += [f"- `{row['id']}` {row['tokens']} tokens, {round(row['share'] * 100)}% of the limit"
                  + (": it will block when it starts" if row["state"] == "over" else "") for row in heavy[:BUDGETS_SHOWN]]
        if len(heavy) > BUDGETS_SHOWN:
            lines.append(f"- and {len(heavy) - BUDGETS_SHOWN} more at {round(lint.NEAR_SHARE * 100)}% or above")
        lines.append("- `devpipe reads` lists every unfinished ticket and the files that will still grow under it.")
    seen = [f"`{ticket_id}` Engineer: {cut(note, LOOP_NOTE_CHARS)}" for ticket_id, note in owner_notes(root, in_phase)]
    seen += [f"`{row['id']}` Reviewer, {row['severity']}, {row['place']}: {cut(row['claim'], LOOP_NOTE_CHARS)}"
             for row in loop_findings(root, in_phase)]
    if seen:
        # Seen in a pilot: an Engineer wrote that the product was wrong and worked around it, the Reviewer
        # recorded it as minor and passed the ticket, and the owner met the fault at the exit demo.
        lines += ["", "## From the loop", "",
                  "What Engineers wrote for you and what the per-ticket Reviewer recorded, on this phase's tickets. "
                  "Read them before you call the phase complete.", ""]
        lines += [f"- {item}" for item in seen[:LOOP_SHOWN]]
        if len(seen) > LOOP_SHOWN:
            lines.append(f"- and {len(seen) - LOOP_SHOWN} more: `devpipe notes --phase {phase}` lists every one.")
    noted = features.summary(root)
    if noted:
        lines += ["", "## Features", "", f"- {noted}. `devpipe feature list` shows each one."]
    lines += ["", "## Verify the repository", ""]
    lines += [f"- `{command}`" + (" (a long suite: it runs at a seam only)" if kind == gates.SEAM else "")
              for command, kind in gates.commands(config)] or ["- No phase gate command is configured in `.devpipe/config.json`."]
    if gates.commands(config):
        lines.append(f"- `devpipe gate --check` shows which of these this tree has passed; `{gates.record_name(phase)}` "
                     "is the record of every run.")
    lines += ["", "## Resume", "", f"- `devpipe run --phase {phase}`",
              "- `devpipe status` shows the tickets and the last run state.",
              "- Read `README.md`, then `docs/RUNBOOK.md`, then `docs/TESTING.md`.", ""]
    (root / "HANDOFF.md").write_text("\n".join(lines), encoding="utf-8")


def triage(root: Path, phase: Optional[int] = None) -> List[Dict[str, Any]]:
    """Every blocked ticket with what its owner needs to decide on it: one row each.

    Row: id, title, phase, reason, detail (the rescue packet's), rounds (Engineer calls spent),
    tokens (input of all calls, from the ledger; 0 when the ledger has no such column),
    waiting (unfinished tickets that cannot start until this one is done), packet.
    """
    everything = tk.load_all(root)
    graph = {ticket.id: ticket.blocked_by for ticket in everything}
    rows: List[Dict[str, Any]] = []
    for ticket in everything:
        if ticket.status != "blocked" or (phase is not None and ticket.phase != phase):
            continue
        work = ticket.work_dir(root)
        packet = work / "RESCUE.md"
        detail = ""
        if packet.is_file():
            detail = next((line[len("- Detail: "):] for line in packet.read_text(encoding="utf-8", errors="replace").splitlines()
                           if line.startswith("- Detail: ")), "")
        tokens = 0
        ledger_file = ledger_path(root, ticket.phase)
        if ledger_file.is_file() and TOTAL_COLUMN in ledger_file.read_text(encoding="utf-8"):
            for line in ledger_file.read_text(encoding="utf-8").splitlines():
                cells = [cell.strip() for cell in line.split("|")]
                if len(cells) > 8 and cells[2] == ticket.id and cells[3].startswith("blocked") and cells[8].isdigit():
                    tokens = int(cells[8])
        rows.append({
            "id": ticket.id, "title": ticket.title, "phase": ticket.phase,
            "reason": str(ticket.meta.get("blocked_reason", "")), "detail": detail,
            "rounds": len(list(work.glob("*-engineer.log"))) if work.is_dir() else 0, "tokens": tokens,
            "waiting": [other.id for other in everything if other.status != "done" and other.id != ticket.id
                        and lint.waits_for(other.id, ticket.id, graph)],
            "packet": f"{tk.TICKET_DIR}/{tk.WORK_DIR}/{ticket.id}/RESCUE.md",
        })
    return rows


def rescue(root: Path, ticket: tk.Ticket, reason: str, detail: str, files: List[str],
           limits: Optional[Dict[str, Any]] = None) -> Path:
    """Write the rescue packet for a blocked ticket: a prompt a stronger model can start from.

    `limits` are the limits in force, so the packet states the profile's file limits rather than a fixed number.
    """
    work = ticket.work_dir(root)
    if limits:
        allowed = (f"the ticket lint allows {limits['max_writes']} `writes` file(s) and {limits['max_tests']} "
                   "`tests` file(s) per ticket (`devpipe limits`). Add the file to this ticket only if it then "
                   "stays within them; otherwise it is fixed by a new ticket that owns that file, which this "
                   "ticket then waits for through `blocked_by`")
    else:
        allowed = ("it is fixed by a new ticket that owns that file, which this ticket then waits for through "
                   "`blocked_by`; `devpipe limits` gives how many `writes` and `tests` files a ticket may list")
    work.mkdir(parents=True, exist_ok=True)
    listed = "\n".join(f"- `.tickets/.work/{ticket.id}/{name}`" for name in files) or "- (none)"
    relative = ticket.path.relative_to(root)
    text = f"""# Rescue: {ticket.id} — {ticket.title}

The automated loop stopped on this ticket and reset the repository to the commit before it.

- Reason: **{reason}**
- Detail: {detail or 'none'}
- Ticket: `{relative}`

## Evidence left by the run

{listed}

## Prompt for a rescue session

Read `{relative}` and the files listed above. The last attempt is saved as a patch; it is
evidence, not a starting point. Find why the ticket's `verify` command fails or why the review
rejected the change, state the cause with the line of evidence that shows it, and then either
(a) implement the ticket so that `{ticket.verify}` exits 0 while touching only its `writes` and
`tests` files, or (b) if the ticket itself is wrong or too large, say so and propose the split
instead of forcing it. When it is fixed, set the ticket's `status: todo` and run
`devpipe run --phase {ticket.phase}` again, or commit your fix and run `devpipe ticket done {ticket.id}`.

If the cause is in a file outside this ticket's `writes` and `tests` (a lint or compile error
on a file another ticket wrote, or an existing test the ticket cannot leave unchanged): {allowed}.
A new ticket's `verify` runs the check that failed here.
"""
    path = work / "RESCUE.md"
    path.write_text(text, encoding="utf-8")
    return path


def phase_commits(root: Path, phase: int) -> "tuple[List[str], Dict[str, List[str]]]":
    """Every commit of the phase: (ticket commits, the others grouped by their tag), oldest first.

    The phase begins where its branch left the main line (the merge base with the default
    branch), or at its first commit tagged `[tickets-PNN]`, `[PNN.T…]` or `[PNN]`, whichever is
    earlier, and runs to HEAD. What lies between is the phase, whoever made it. Work that
    lands before the tickets are written belongs to it as much as a ticket does: the retro of
    the phase before, a configuration change, a plan fix, the features accepted for this phase.
    """
    lines = git.git(root, "log", "--first-parent", "--reverse", "--format=%h %s").splitlines()
    begins = re.compile(rf"^\S+ \[(tickets-)?P{phase:02d}[.\]]")
    start = next((index for index, line in enumerate(lines) if begins.match(line)), len(lines))
    # Commits this branch has and the main line has not. Of the names the main line may go by,
    # the one nearest to HEAD is the one that is up to date.
    head = git.git(root, "rev-parse", "HEAD")
    origin = git.git(root, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD", check=False)
    ahead = []
    for name in [origin, "main", "master"]:
        base = git.git(root, "merge-base", "HEAD", name, check=False) if name else ""
        if base and base != head:
            ahead.append(int(git.git(root, "rev-list", "--count", "--first-parent", f"{base}..HEAD")))
    if ahead:
        start = min(start, max(len(lines) - min(ahead), 0))
    ticket = re.compile(rf"^\S+ \[P{phase:02d}\.T\d+\]")
    tickets: List[str] = []
    others: Dict[str, List[str]] = {}
    for line in lines[start:]:
        if ticket.match(line):
            tickets.append(line)
            continue
        tag = re.match(r"^\S+ (\[[^\]]+\])", line)
        others.setdefault(f"`{tag.group(1)}`" if tag else "no tag", []).append(line)
    return tickets, others


def owner_notes(root: Path, in_phase: List[tk.Ticket]) -> List["tuple[str, str]"]:
    """(ticket id, note) for every line an Engineer wrote under `For the owner:` on a ticket of the phase."""
    found = []
    for ticket in in_phase:
        path = root / tk.TICKET_DIR / tk.WORK_DIR / ticket.id / "owner-notes.md"
        if path.is_file():
            found += [(ticket.id, line.strip()) for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                      if line.strip()]
    return found


def engineer_notes(root: Path, in_phase: List[tk.Ticket]) -> str:
    """The brief's table of Engineers' notes for the owner."""
    rows = [f"| `{ticket_id}` | {note.replace('|', '/')} |" for ticket_id, note in owner_notes(root, in_phase)]
    if not rows:
        return "None: no Engineer left a note under `For the owner:`."
    return "| Ticket | Note |\n|---|---|\n" + "\n".join(rows)


def loop_findings(root: Path, in_phase: List[tk.Ticket]) -> List[Dict[str, str]]:
    """Every finding the in-loop Reviewer recorded in a ticket's latest review: {id, severity, place, claim}."""
    rows: List[Dict[str, str]] = []
    for ticket in in_phase:
        path = root / tk.TICKET_DIR / tk.WORK_DIR / ticket.id / "review.json"
        if not path.is_file():
            continue
        try:
            found = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for item in found.get("findings") or []:
            place = str(item.get("file") or "").strip()
            line = item.get("line")
            place = f"`{place}:{line}`" if place and line else f"`{place}`" if place else "(no file given)"
            rows.append({"id": ticket.id, "severity": str(item.get("severity") or "?"), "place": place,
                         "claim": " ".join(str(item.get("claim") or "").split())})
    return rows


def per_ticket_findings(root: Path, in_phase: List[tk.Ticket]) -> str:
    """Every finding the in-loop Reviewer recorded, whatever its verdict.

    Seen in a pilot: the Reviewer passed all 100 tickets of a phase and still recorded four
    findings, which only `review.json` held. The phase reviewer found three of them again as its
    own and never saw the fourth. They are listed in the brief so a round starts from them.
    """
    listed = [f"| `{row['id']}` | {row['severity']} | {row['place']} | {row['claim']} |" for row in loop_findings(root, in_phase)]
    if not listed:
        return "None: the Reviewer recorded no finding on any ticket of this phase."
    return ("| Ticket | Severity | Where | Claim |\n|---|---|---|---|\n" + "\n".join(listed))


def gate_rows(gate_results: List[Dict[str, Any]]) -> str:
    """The brief's gate table: for each command what it showed, on which commit, and where its log is."""
    rows = []
    for gate in gate_results:
        if gate.get("owed") == "merge":
            result = "owed before the merge: not run for this round"
        elif gate.get("owed") == "red":
            result = "not run: a quick command is not green"
        elif not gate.get("ran", True):
            result = "green on this tree: not run again"
        else:
            result = f"exit {gate['code']}" + (f", but it reused an earlier result (`{gate['stale']}`): its tests "
                                               "did not run" if gate.get("stale") else "")
        commit = str(gate.get("commit") or gate.get("since") or "")[:8]
        took = f"{gate['seconds']} s" if gate.get("ran", True) and "seconds" in gate else ""
        rows.append(f"| `{gate['command']}` | {result} | {commit} | {took} | `{gate.get('log', '')}` |")
    return "\n".join(rows) or "| (no phase gate configured) | n/a | | | |"


def gate_owed(phase: int, gate_results: List[Dict[str, Any]]) -> str:
    """One paragraph on the long suites left for the merge, with what changed since each passed; '' when none is."""
    owed = [gate for gate in gate_results if gate.get("owed") == "merge"]
    if not owed:
        return ""
    lines = [f"Owed before the merge, and run by `devpipe gate --phase {phase}`, not by you:", ""]
    for gate in owed:
        changed = gate.get("changed") or []
        shown = ", ".join(f"`{path}`" for path in changed[:8]) + (f" and {len(changed) - 8} more" if len(changed) > 8 else "")
        lines.append(f"- `{gate['command']}`: last green on {str(gate.get('since') or '')[:8]}; changed since: {shown}")
    return "\n".join(lines) + "\n\n"


def review_brief(root: Path, phase: int, gate_results: List[Dict[str, Any]]) -> Path:
    """Write the phase-end brief for the owner's independent reviewer."""
    in_phase = tk.load_phase(root, phase)
    rows = "\n".join(f"| `{ticket.id}` | {ticket.title} | {ticket.status} | `{ticket.verify}` |" for ticket in in_phase)
    gate_table = gate_rows(gate_results)
    owed = gate_owed(phase, gate_results)
    ticket_commits, other_commits = phase_commits(root, phase)
    commits = "\n".join(ticket_commits) or "(none)"
    others = "\n\n".join(f"{tag} ({len(found)})\n\n```\n" + "\n".join(found) + "\n```" for tag, found in other_commits.items()) \
        or "None: the phase holds ticket commits only."
    reviewed = per_ticket_findings(root, in_phase)
    noted = engineer_notes(root, in_phase)
    path = root / "docs" / "qa" / "reviews" / f"phase-{phase:02d}.md"
    rounds = keep_review_round(path)
    earlier = ("- Earlier review rounds, with their findings and answers: "
               + ", ".join(f"`{kept.relative_to(root)}`" for kept in rounds) + "\n") if rounds else ""
    look = ""
    if ui.screens(ui.read(root) or ""):
        look = ("\n7. For each screen this phase built: `python3 tools/devpipe/run.py ui compare S-0N`, then look at\n"
                "   `.tickets/.work/ui-compare/S-0N.png`: the mockup, the built screen and their difference, side by side.")
    text = f"""# Review brief: phase {phase:02d}

Written by `devpipe run` on {now()}. Run it with the project's reviewer agent on a model other
than the one that wrote the code: "Review `docs/qa/reviews/phase-{phase:02d}.md`".

## Scope

- Branch: `phase/{phase:02d}`
- Design: `design/SPECIFICATION.md`, `design/ARCHITECTURE.md`, `design/DECISIONS.md`
- Per-ticket record: `docs/ledger/phase-{phase:02d}.md`
{earlier}
### Commits

Ticket commits, one per ticket event:

```
{commits}
```

### Other commits in the phase

Not made for a ticket, and part of what is reviewed: toolkit refreshes, tickets written or
amended, features folded in, the runner's own notes.

{others}

### Tickets

| Ticket | Title | Status | Verify |
|---|---|---|---|
{rows}

### Findings already recorded in the loop

Each ticket's own review, whatever its verdict. These are known: answer them in the Answers
section rather than raising them again as your own findings.

{reviewed}

### Engineer notes for the owner

What each ticket's Engineer wrote under `For the owner:`. The owner answers them; a note that names a
fault in the product, the plan or a ticket is yours to check as well.

{noted}

## Phase gate (run by the runner)

Each command is run once per tree: one that passed on a commit which differs from this one only in
files no gate reads is not run again. Every run is a line in `{gates.record_name(phase)}`. Check this
table against it and against the repository; do not run these commands yourself.

| Command | Result | On commit | Took | Log |
|---|---|---|---|---|
{gate_table}

{owed}## What to examine

1. Does each ticket's diff do what its ticket and the cited requirement say, and nothing else?
2. Do the invariants in `design/ARCHITECTURE.md` still hold across the phase as a whole?
3. Would each test fail if the behaviour it names were broken?
4. Handoff: following README, then RUNBOOK, then TESTING only, can a stranger build and test this?
5. Each row of "Findings already recorded in the loop": does it still stand, and was it answered?
6. Every commit under "Other commits in the phase": does it change code, a check, a ticket's
   acceptance or the toolkit in a way no ticket's review covered?{look}

## Findings

*(Reviewer: one entry per provable finding with severity, file:line, trigger, effect and evidence;
then the commands you ran, the verdict CLEAN or CHANGES REQUESTED, and open questions. Write over this note.)*

## Answers

*(Per finding: fixed in `<commit>`, or the reason it stands.)*

Status: OPEN
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# The brief's own placeholder under "## Findings": a note in italics that begins like this.
_FINDINGS_PLACEHOLDER = "*(Reviewer: one entry per provable finding"


def was_reviewed(text: str) -> bool:
    """True when a brief holds a review: anything under "## Findings" besides the placeholder, or a status that is no longer OPEN.

    Seen in a pilot, three phases running: the reviewer wrote its findings below the placeholder
    and left the placeholder standing. Judged by the placeholder's absence, the brief counted as
    never reviewed, and the next completion wrote over the round.
    """
    section = text.split("\n## Findings", 1)[1] if "\n## Findings" in text else ""
    section = re.split(r"^## ", section, maxsplit=1, flags=re.MULTILINE)[0]
    section = re.sub(r"\*\(Reviewer:.*?\)\*", "", section, flags=re.DOTALL)
    status = re.search(r"^Status:\s*(\S+)", text, flags=re.MULTILINE)
    return bool(section.strip()) or bool(status and status.group(1).upper() != "OPEN")


def keep_review_round(brief: Path) -> List[Path]:
    """Keep a reviewed brief as the next `phase-NN-round-K.md` before it is written again; return every round kept.

    The brief is regenerated at each completion of the phase. Without this, each review round's
    findings and the owner's answers had to be saved by hand before the run that fixed them, or they
    were overwritten. A brief nobody wrote into is not kept; one identical to a round already kept
    is not kept twice.
    """
    stem = brief.stem
    def kept_rounds() -> List[Path]:
        found = []
        for candidate in brief.parent.glob(f"{stem}-round-*.md"):
            number = candidate.stem[len(stem) + len("-round-"):]
            if number.isdigit():
                found.append((int(number), candidate))
        return [candidate for _, candidate in sorted(found)]
    rounds = kept_rounds()
    if brief.is_file():
        text = brief.read_text(encoding="utf-8")
        if was_reviewed(text) and not any(
                kept.read_text(encoding="utf-8") == text for kept in rounds):
            number = 1 + max([int(kept.stem.rsplit("-", 1)[1]) for kept in rounds] or [0])
            target = brief.with_name(f"{stem}-round-{number}.md")
            target.write_text(text, encoding="utf-8")
            rounds = kept_rounds()
    return rounds
