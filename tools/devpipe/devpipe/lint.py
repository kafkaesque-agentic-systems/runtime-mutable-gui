"""Deterministic lints for the pipeline's artifacts.

Purpose: turn "zero ambiguity", "no tool choice left to the agent" and "fits a
128K session" into checks a script can fail. Each stage ends by running its
lint; the runner refuses to start a phase whose tickets do not pass.
Dependencies: fm, tickets, tokens.
Side effects: reads files; `lint_tickets` may call the token-count endpoint.
"""
from __future__ import annotations

import fnmatch
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import fm, tickets as tk, tokens

ERROR, WARN = "error", "warn"

SPEC_SECTIONS = ["Problem", "Users", "Requirements", "Non-functional requirements",
                 "Data model", "Edge cases", "Out of scope", "Not yet specified"]
ARCH_SECTIONS = ["Components", "Boundaries", "Data flow", "Invariants", "Test seams"]
TICKET_SECTIONS = ["Behaviour", "Acceptance", "Out of scope"]
PLAN_FIELDS = ["Files", "Libraries", "Commands", "Tests", "Gate", "Requirements"]
# Templates mark every blank as <<…>>, so an unfilled blank is unmistakable.
PLACEHOLDERS = re.compile(r"\b(TBD|TODO|FIXME|XXX)\b|\?\?\?|<<[^>]*>>")
# Phrases that leave a choice to whoever executes the plan.
VAGUE = re.compile(r"\b(or similar|or equivalent|as appropriate|as needed|if needed|appropriate|suitable|"
                   r"choose|pick an?|decide|evaluate|investigate|research|explore options|some kind of|etc\.?)\b",
                   re.IGNORECASE)
# Body words of a project agent. On the constrained tier the agent file takes room from a
# small window, so the budget is a limit and going over it is an error. On the Claude tier
# the window is not the constraint: the words are a cost on every call, and the budget is a
# guide, so going over it is a warning and does not stop a run.
WORD_BUDGET = {
    "opencode": {"engineer": 500, "reviewer": 350, "diagnostic": 300},
    "claude": {"engineer": 2500, "reviewer": 1200, "diagnostic": 900},
}
WORD_BUDGET_IS_A_LIMIT = {"opencode": True, "claude": False}
AGENT_DIRS = {"opencode": ".opencode/agents", "claude": ".claude/agents"}


@dataclass
class Issue:
    level: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():5} {self.where}: {self.message}"


def has_errors(issues: List[Issue]) -> bool:
    return any(issue.level == ERROR for issue in issues)


def _read(path: Path, issues: List[Issue]) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        issues.append(Issue(ERROR, str(path), "file is missing"))
        return None


def _sections(text: str, level: int = 2) -> Dict[str, str]:
    """Map each heading of `level` to the text under it."""
    marker = "#" * level + " "
    found: Dict[str, str] = {}
    name, lines = "", []
    for line in text.splitlines():
        if line.startswith(marker):
            if name:
                found[name] = "\n".join(lines)
            name, lines = line[len(marker):].strip(), []
        elif name:
            lines.append(line)
    if name:
        found[name] = "\n".join(lines)
    return found


def _placeholders(text: str, where: str, issues: List[Issue], blanks_only: bool = False) -> None:
    """Report unfilled blanks; `blanks_only` skips the TODO words (agent rules mention them)."""
    pattern = re.compile(r"<<[^>]*>>") if blanks_only else PLACEHOLDERS
    for number, line in enumerate(text.splitlines(), start=1):
        match = pattern.search(line)
        if match:
            issues.append(Issue(ERROR, f"{where}:{number}", f"placeholder {match.group(0)!r} left in the text"))


def _is_empty_section(text: str) -> bool:
    return text.strip().lower() in ("", "none", "none.", "- none", "- none.")


def requirement_ids(spec_text: str) -> List[str]:
    return re.findall(r"^### (R-\d{3})\b", spec_text, flags=re.MULTILINE)


def stack_names(stack_text: str) -> Set[str]:
    """Lower-cased names from the first column of the STACK table."""
    names = set()
    for line in stack_text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and len(cells) >= 2 and not set(cells[0]) <= set("-: ") and cells[0].lower() != "name":
            names.add(cells[0].strip("`").lower())
    return names


def lint_spec(root: Path, allow_open: bool = False) -> List[Issue]:
    """Check `design/`: structure, requirement ids, acceptance lines, no open items."""
    issues: List[Issue] = []
    design = root / "design"
    spec = _read(design / "SPECIFICATION.md", issues)
    arch = _read(design / "ARCHITECTURE.md", issues)
    decisions = _read(design / "DECISIONS.md", issues)
    glossary = _read(design / "GLOSSARY.md", issues)
    stack = _read(design / "STACK.md", issues)
    if spec is not None:
        where = "design/SPECIFICATION.md"
        sections = _sections(spec)
        for name in SPEC_SECTIONS:
            if name not in sections:
                issues.append(Issue(ERROR, where, f"section '## {name}' is missing"))
        _placeholders(spec, where, issues)
        blocks = re.split(r"^### ", sections.get("Requirements", ""), flags=re.MULTILINE)[1:]
        if not blocks:
            issues.append(Issue(ERROR, where, "no requirement found; each one starts with '### R-001 — title'"))
        seen: Set[str] = set()
        for block in blocks:
            title = block.splitlines()[0]
            match = re.match(r"(R-\d{3}) — \S", title)
            if not match:
                issues.append(Issue(ERROR, where, f"requirement heading {title!r} must read 'R-001 — title'"))
                continue
            if match.group(1) in seen:
                issues.append(Issue(ERROR, where, f"{match.group(1)} is defined twice"))
            seen.add(match.group(1))
            if not re.search(r"^Acceptance:\s*\S", block, flags=re.MULTILINE):
                issues.append(Issue(ERROR, where, f"{match.group(1)} has no 'Acceptance:' line"))
        if "Out of scope" in sections and _is_empty_section(sections["Out of scope"]):
            issues.append(Issue(WARN, where, "'Out of scope' is empty; name what this version will not do"))
        if "Not yet specified" in sections and not _is_empty_section(sections["Not yet specified"]):
            issues.append(Issue(WARN if allow_open else ERROR, where,
                                "'Not yet specified' still lists open items; resolve them or write 'None.'"))
    if arch is not None:
        where = "design/ARCHITECTURE.md"
        sections = _sections(arch)
        for name in ARCH_SECTIONS:
            if name not in sections:
                issues.append(Issue(ERROR, where, f"section '## {name}' is missing"))
        if not re.search(r"\bI-\d{2}\b", sections.get("Invariants", "")):
            issues.append(Issue(ERROR, where, "no invariant found; write each as '- **I-01** …'"))
        _placeholders(arch, where, issues)
    if decisions is not None:
        where = "design/DECISIONS.md"
        if not re.search(r"^## D-\d{2} — \S", decisions, flags=re.MULTILINE):
            issues.append(Issue(ERROR, where, "no decision found; each one starts with '## D-01 — title'"))
        for block in re.split(r"^## ", decisions, flags=re.MULTILINE)[1:]:
            title = block.splitlines()[0]
            status = re.search(r"^Status:\s*(\w+)", block, flags=re.MULTILINE)
            if not title.startswith("D-"):
                continue
            if not status or status.group(1) not in ("ACCEPTED", "PROPOSED", "SUPERSEDED"):
                issues.append(Issue(ERROR, where, f"{title.split(' ')[0]} needs 'Status: ACCEPTED|PROPOSED|SUPERSEDED'"))
            elif status.group(1) == "PROPOSED":
                issues.append(Issue(WARN if allow_open else ERROR, where,
                                    f"{title.split(' ')[0]} is still PROPOSED; the owner ratifies it before planning"))
        _placeholders(decisions, where, issues)
    if glossary is not None and len(glossary.split()) < 10:
        issues.append(Issue(WARN, "design/GLOSSARY.md", "glossary is nearly empty"))
    if stack is not None:
        where = "design/STACK.md"
        rows = 0
        for number, line in enumerate(stack.splitlines(), start=1):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not line.strip().startswith("|") or set("".join(cells)) <= set("-: ") or cells[0].lower() == "name":
                continue
            rows += 1
            if len(cells) < 4 or not cells[1] or not cells[3]:
                issues.append(Issue(ERROR, f"{where}:{number}", "row needs Name, Version, Role and Source"))
            elif re.search(r"latest|newest|current|\*", cells[1], re.IGNORECASE):
                issues.append(Issue(ERROR, f"{where}:{number}", f"version {cells[1]!r} is not pinned"))
        if rows == 0:
            issues.append(Issue(ERROR, where, "no stack row found; the table is | Name | Version | Role | Source |"))
        _placeholders(stack, where, issues)
    return issues


def plan_phases(plan_text: str) -> Dict[int, str]:
    """Return {phase: the text of its section}."""
    result: Dict[int, str] = {}
    for phase_block in re.split(r"^## (?=Phase \d+)", plan_text, flags=re.MULTILINE)[1:]:
        head = re.match(r"Phase (\d+)", phase_block)
        if head:
            result[int(head.group(1))] = phase_block
    return result


def plan_steps(plan_text: str) -> Dict[int, List[Tuple[str, str, str]]]:
    """Return {phase: [(step id 'N.M', title, block text)]}."""
    result: Dict[int, List[Tuple[str, str, str]]] = {}
    for phase_block in re.split(r"^## (?=Phase \d+)", plan_text, flags=re.MULTILINE)[1:]:
        head = re.match(r"Phase (\d+)", phase_block)
        if not head:
            continue
        steps = []
        for step_block in re.split(r"^### (?=Step )", phase_block, flags=re.MULTILINE)[1:]:
            match = re.match(r"Step (\d+\.\d+) — (.*)", step_block)
            if match:
                steps.append((match.group(1), match.group(2).strip(), step_block))
        result[int(head.group(1))] = steps
    return result


def lint_plan(root: Path) -> List[Issue]:
    """Check DEV_PLAN.md: every step names files, libraries, commands, tests, gate, requirements."""
    issues: List[Issue] = []
    where = "DEV_PLAN.md"
    plan = _read(root / where, issues)
    if plan is None:
        return issues
    stack = stack_names((root / "design" / "STACK.md").read_text(encoding="utf-8")) if (root / "design" / "STACK.md").is_file() else set()
    spec_path = root / "design" / "SPECIFICATION.md"
    required = set(requirement_ids(spec_path.read_text(encoding="utf-8"))) if spec_path.is_file() else set()
    _placeholders(plan, where, issues)
    for number, line in enumerate(plan.splitlines(), start=1):
        # Only the lines an agent executes from: step fields, goals and exit demos.
        match = VAGUE.search(line) if line.startswith(("- ", "**Goal:**", "**Exit demo:**")) else None
        if match:
            issues.append(Issue(ERROR, f"{where}:{number}", f"{match.group(0)!r} leaves a choice to the executing agent; state the choice"))
    phases = plan_steps(plan)
    if 0 not in phases:
        issues.append(Issue(ERROR, where, "'## Phase 0 — Foundation' is missing; it is what the init stage executes"))
    covered: Set[str] = set()
    for phase_block in re.split(r"^## (?=Phase \d+)", plan, flags=re.MULTILINE)[1:]:
        title = phase_block.splitlines()[0]
        if not re.match(r"Phase \d+ — \S", title):
            issues.append(Issue(ERROR, where, f"phase heading {title!r} must read 'Phase 1 — name'"))
        for marker in ("**Goal:**", "**Exit demo:**"):
            if marker not in phase_block:
                issues.append(Issue(ERROR, where, f"{title}: {marker} is missing"))
    for phase, steps in sorted(phases.items()):
        if not steps:
            issues.append(Issue(ERROR, where, f"Phase {phase} has no '### Step {phase}.1 — title'"))
        for step_id, _title, block in steps:
            label = f"{where} step {step_id}"
            if not step_id.startswith(f"{phase}."):
                issues.append(Issue(ERROR, label, f"step id must start with the phase number {phase}"))
            fields = {match.group(1): match.group(2).strip()
                      for match in re.finditer(r"^- (\w+):(.*)$", block, flags=re.MULTILINE)}
            for name in PLAN_FIELDS:
                if not fields.get(name):
                    issues.append(Issue(ERROR, label, f"'- {name}:' is missing or empty (write 'none' when there is none)"))
            if fields.get("Files") and not re.search(r"`[^`]+`", fields["Files"]):
                issues.append(Issue(ERROR, label, "Files must list exact paths in backticks"))
            if fields.get("Commands") and fields["Commands"].lower() != "none" and "`" not in fields["Commands"]:
                issues.append(Issue(ERROR, label, "Commands must be literal commands in backticks"))
            libraries = fields.get("Libraries", "")
            if libraries and libraries.lower() != "none":
                for name in [part.strip().strip("`").lower() for part in libraries.split(",")]:
                    # The whole name ("jetpack compose"), or its first word when a version follows ("pyjwt 2.8").
                    if name and name not in stack and name.split(" ")[0] not in stack:
                        issues.append(Issue(ERROR, label, f"library {name!r} is not in design/STACK.md"))
            covered.update(re.findall(r"R-\d{3}", fields.get("Requirements", "")))
    for missing in sorted(required - covered):
        issues.append(Issue(ERROR, where, f"{missing} is not referenced by any step"))
    for unknown in sorted(covered - required) if required else []:
        issues.append(Issue(ERROR, where, f"{unknown} is referenced but not defined in the specification"))
    return issues


def extract_section(text: str, key: str) -> Optional[str]:
    """Return the part of a document a `section:` entry points at, or None.

    A heading that contains `key` yields everything down to the next heading of
    the same or a higher level; otherwise every line that mentions `key`, each
    with its indented continuation lines.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        heading = re.match(r"(#+) ", line)
        if heading and key in line:
            level = len(heading.group(1))
            end = index + 1
            while end < len(lines):
                other = re.match(r"(#+) ", lines[end])
                if other and len(other.group(1)) <= level:
                    break
                end += 1
            return "\n".join(lines[index:end])
    picked: List[str] = []
    index = 0
    while index < len(lines):
        if key in lines[index]:
            picked.append(lines[index])
            index += 1
            while index < len(lines) and lines[index].startswith((" ", "\t")) and lines[index].strip():
                picked.append(lines[index])
                index += 1
        else:
            index += 1
    return "\n".join(picked) if picked else None


def read_entry_text(root: Path, entry: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Return (text the entry selects, problem). Text is None when it cannot be resolved."""
    path = root / str(entry.get("path", ""))
    if not path.is_file():
        return None, "file does not exist"
    text = path.read_text(encoding="utf-8", errors="replace")
    if "lines" in entry:
        match = re.fullmatch(r"(\d+)-(\d+)", str(entry["lines"]))
        if not match or int(match.group(1)) < 1 or int(match.group(2)) < int(match.group(1)):
            return None, f"lines {entry['lines']!r} must look like \"1-80\""
        return "\n".join(text.splitlines()[int(match.group(1)) - 1:int(match.group(2))]), ""
    if "section" in entry:
        section = extract_section(text, str(entry["section"]))
        return (section, "") if section is not None else (None, f"section {entry['section']!r} not found")
    return text, ""


def read_manifest_size(root: Path, ticket: tk.Ticket, counter: tokens.Counter) -> Tuple[int, List[Tuple[int, str]]]:
    """Tokens of a ticket's read manifest as the files are now: (total, [(tokens, entry)] largest first).

    An entry that cannot be resolved counts nothing; `lint_tickets` is where that is an error.
    """
    sizes: List[Tuple[int, str]] = []
    for entry in ticket.read:
        text, _problem = read_entry_text(root, entry)
        if text is None:
            continue
        size, _exact = counter.count(text)
        sizes.append((size, f"{_entry_name(entry)} {size}"))
    sizes.sort(key=lambda item: -item[0])
    return sum(size for size, _label in sizes), sizes


def shell_syntax(command: str) -> str:
    """Why `sh` cannot parse `command`, or '' when it can (or there is nothing to parse).

    `sh -n` reads the command without running any of it: no build starts and nothing is
    written. A command that fails here would fail the same way in a run, after an Engineer
    round has been spent on the ticket.
    """
    if not command.strip():
        return ""
    try:
        done = subprocess.run(["sh", "-n", "-c", command], capture_output=True, text=True, timeout=10,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if done.returncode == 0:
        return ""
    lines = [line.strip() for line in done.stderr.splitlines() if line.strip()]
    return lines[0] if lines else f"sh -n exits {done.returncode}"


def _entry_name(entry: Dict[str, Any]) -> str:
    """A read entry as it is shown to a person: the path and the part of it that is read."""
    part = f" lines {entry['lines']}" if "lines" in entry else f" section {entry['section']}" if "section" in entry else ""
    return f"`{entry.get('path', '')}`{part}"


# Share of limits.read_tokens from which a ticket is reported as near its budget.
NEAR_SHARE = 0.8


def read_report(root: Path, config: Dict[str, Any], phase: Optional[int] = None,
                counter: Optional[tokens.Counter] = None) -> List[Dict[str, Any]]:
    """What the read manifest of every unfinished ticket weighs now, largest first.

    Each row: id, status, tokens, share (of limits.read_tokens), state (over | near | ok),
    largest (the heaviest entry) and watch (what will change the size before the ticket
    runs: a file read whole or by line range that a ticket still to run writes, a file not
    written yet). The runner measures a ticket only when it starts; this is the same
    measurement for all of them at once, so they can be put right before a run.
    """
    limits = config["limits"]
    limit = int(limits["read_tokens"])
    counter = counter or tokens.Counter(config.get("tokens") or {})
    loaded = tk.load_all(root)
    graph = {ticket.id: ticket.blocked_by for ticket in loaded}
    writers: Dict[str, List[tk.Ticket]] = {}
    for ticket in loaded:
        for path in ticket.writes + ticket.tests:
            writers.setdefault(path, []).append(ticket)
    rows: List[Dict[str, Any]] = []
    for ticket in loaded:
        if ticket.status == "done" or ticket.mode == "hitl" or (phase is not None and ticket.phase != phase):
            continue
        total, entries, watch = 0, [], []
        for entry in ticket.read:
            path = str(entry.get("path", ""))
            # Unfinished tickets that write this file and run first: a lower number, or one this ticket waits for.
            pending = ", ".join(maker.id for maker in writers.get(path, []) if maker.status != "done" and maker.id != ticket.id and (
                (maker.phase, maker.number) < (ticket.phase, ticket.number) or waits_for(ticket.id, maker.id, graph)))
            text, problem = read_entry_text(root, entry)
            if text is None:
                if problem != "file does not exist" or not pending:
                    watch.append(f"{_entry_name(entry)}: {problem}")
                    continue
                size = int(limits["write_lines"]) * 12    # as the lint budgets a file an earlier ticket creates
                watch.append(f"`{path}` is not written yet ({pending}); counted at {size}")
            else:
                size, _exact = counter.count(text)
                if pending and "lines" in entry:
                    watch.append(f"{_entry_name(entry)} may shift: {pending} still to write it")
                elif pending and "section" not in entry:
                    watch.append(f"`{path}` is read whole and will grow: {pending} still to write it")
            total += size
            entries.append((size, f"{_entry_name(entry)} {size}"))
        entries.sort(key=lambda item: -item[0])
        rows.append({"id": ticket.id, "status": ticket.status, "tokens": total, "share": total / limit if limit else 0.0,
                     "state": "over" if total > limit else "near" if total >= NEAR_SHARE * limit else "ok",
                     "largest": entries[0][1] if entries else "", "watch": watch})
    rows.sort(key=lambda row: -row["tokens"])
    return rows


def _cycle(graph: Dict[str, List[str]]) -> Optional[List[str]]:
    state: Dict[str, int] = {}

    def visit(node: str, trail: List[str]) -> Optional[List[str]]:
        if state.get(node) == 1:
            return trail[trail.index(node):] + [node]
        if state.get(node) == 2:
            return None
        state[node] = 1
        for nxt in graph.get(node, []):
            found = visit(nxt, trail + [node])
            if found:
                return found
        state[node] = 2
        return None

    for start in graph:
        found = visit(start, [])
        if found:
            return found
    return None


def waits_for(start: str, goal: str, graph: Dict[str, List[str]]) -> bool:
    """True when ticket `start` waits, directly or through other tickets, for ticket `goal`."""
    seen: Set[str] = set()
    stack = list(graph.get(start, []))
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        if node not in seen:
            seen.add(node)
            stack.extend(graph.get(node, []))
    return False


# Two faults a ticket's Acceptance can show before a run, both seen as blocks in a long phase and
# both invisible to the read-manifest and file-conflict checks: a package the ticket leans on that
# an unfinished ticket creates and it does not wait for, and a file it says it changes but does
# not own. They are judged against the files git tracks, so they hold for any language whose
# packages are folders.
_PACKAGE_RE = re.compile(r"`([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)`")
_GAINS_RE = re.compile(r"`?\b([A-Z][A-Za-z0-9]*)`?\s+gains\b")


def tracked_files(root: Path) -> List[str]:
    """Paths git tracks in the repository, or [] where there is no repository."""
    try:
        done = subprocess.run(["git", "ls-files"], cwd=str(root), capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return done.stdout.splitlines() if done.returncode == 0 else []


def _package_dependencies(ticket: tk.Ticket, tracked: List[str], graph: Dict[str, List[str]],
                          produced: Dict[str, List[str]], where: str, issues: List[Issue]) -> None:
    """A package the Acceptance names must exist, or the ticket must wait for the one that creates it.

    Seen in a pilot: a ticket named a package for a type that an earlier-numbered ticket writes and
    did not wait for it, so in a parallel run it started in a tree where the type did not exist and
    blocked as a ticket defect. The read-manifest check could not see it: the ticket read no file
    of that package. A dotted name counts as a package when another ticket writes a file under the
    folder it spells (`a.b.c` → `a/b/c/`) and no tracked file is there yet.
    """
    accept = _sections(ticket.body).get("Acceptance", "")
    for dotted in sorted({match.group(1) for match in _PACKAGE_RE.finditer(accept)}):
        fragment = "/" + dotted.replace(".", "/") + "/"
        makers = sorted({maker for path, ids in produced.items() if fragment in "/" + path
                         for maker in ids if maker != ticket.id})
        if not makers or any(fragment in "/" + path for path in tracked):
            continue
        if any(fragment in "/" + path for path in ticket.writes + ticket.tests):
            continue        # the ticket creates the package itself
        if any(waits_for(ticket.id, maker, graph) for maker in makers):
            continue
        issues.append(Issue(ERROR, where, f"Acceptance names package `{dotted}`, which no file in the tree "
                                          f"provides yet; {', '.join(makers)} create it and 'blocked_by' waits "
                                          "for none of them"))


def _acceptance_owns_its_files(ticket: tk.Ticket, tracked: List[str], where: str, issues: List[Issue]) -> None:
    """A file the Acceptance says gains something must be the ticket's own.

    Seen in a pilot: an Acceptance line read "`OrderServiceTest` gains: …" while `tests` named
    another file only. The runner commits only a ticket's own files, so those tests would have
    been discarded; the Engineer stopped and the ticket blocked.
    """
    accept = _sections(ticket.body).get("Acceptance", "")
    owned = {Path(path).stem for path in ticket.writes + ticket.tests}
    for name in sorted({match.group(1) for match in _GAINS_RE.finditer(accept)} - owned):
        existing = sorted(path for path in tracked if Path(path).stem == name)
        if not existing:
            # Nothing of that name exists yet: another ticket introduces it, which the package
            # and read-manifest checks cover.
            continue
        issues.append(Issue(ERROR, where, f"Acceptance says `{name}` gains something, but `{existing[0]}` is in neither "
                                          "'writes' nor 'tests': the runner commits only those files, so the "
                                          "change would be discarded"))


# Two mistakes seen in fix tickets, caught only by the ticket review, and one red phase gate, all
# cheap to see in a ticket's header.
_DOCUMENT_SUFFIXES = {".md", ".txt", ".adoc", ".rst"}


def _red_check_mixes_documents(ticket: tk.Ticket, where: str, issues: List[Issue]) -> None:
    """A red-checked ticket that writes code and a document proves nothing about the code.

    Seen in a pilot: a draft wrote a service and two documents, with greps on the documents in its
    verify. The red check puts every `writes` file back, the greps then fail, and verify fails
    whether or not any test needs the code change.
    """
    documents = [path for path in ticket.writes if Path(path).suffix.lower() in _DOCUMENT_SUFFIXES]
    if documents and len(documents) < len(ticket.writes):
        issues.append(Issue(WARN, where, f"red_check reverts {', '.join(documents)} with the code, so a check on "
                                         "the document fails verify whatever the code does; give the document its "
                                         "own ticket with red_check: false"))


def _whole_suite(ticket: tk.Ticket, config: Dict[str, Any], where: str, issues: List[Issue]) -> None:
    """A ticket writing under a `whole_suite` prefix runs that test task whole.

    Seen in a pilot: a ticket's verify listed fourteen test classes and left out the one whose
    assertion its change broke, so the phase gate went red; the ticket review had already added
    classes to three other tickets' lists. A hand-picked list is the fault, whoever picks it.
    """
    for prefix, task in (config.get("whole_suite") or {}).items():
        if not any(path.startswith(str(prefix)) for path in ticket.writes):
            continue
        runs = re.search(rf"(?<![\w:-]){re.escape(str(task))}(?![\w-])((?:\s+--tests\s+\S+)*)", ticket.verify)
        if not runs:
            issues.append(Issue(ERROR, where, f"writes under `{prefix}` but `verify` does not run `{task}`; run it "
                                              "whole (whole_suite in .devpipe/config.json)"))
        elif runs.group(1).strip():
            issues.append(Issue(ERROR, where, f"writes under `{prefix}` but runs `{task}` filtered with --tests; run "
                                              "it whole, since a hand-picked list misses the tests the gate then "
                                              "fails (whole_suite in .devpipe/config.json)"))


def _refined_tests(selected: List[tk.Ticket], by_id: Dict[str, tk.Ticket], root: Path, issues: List[Issue]) -> None:
    """A ticket that another ticket's text says "refines it" lists that ticket's test files.

    Seen in a pilot: a ticket's acceptance said "a row without a name stays NEW (P02-T08
    refines it)" and its test pinned that interim behaviour. The refining ticket changed the
    behaviour without that test file under `tests:`, could not touch it, and blocked.
    """
    for earlier in selected:
        for later_id in sorted(set(re.findall(r"\b(P\d{2,3}-T\d{2,4}) refines\b", earlier.body))):
            later = by_id.get(later_id)
            if later is None or later.id == earlier.id or later.status == "done":
                continue
            missing = [path for path in earlier.tests if path not in later.tests]
            if missing:
                issues.append(Issue(ERROR, str(later.path.relative_to(root)), (
                    f"{earlier.id} says {later.id} refines it, and {earlier.id}'s test pins the behaviour to be "
                    f"changed: list {', '.join(f'`{path}`' for path in missing)} under this ticket's `tests:`")))


SHARED_RESOURCE = re.compile(r"(?<![\w./-])docker(?:-compose)?(?![\w/-])")
SAME_FILE_TICKETS = 3


def _shared_files_and_resources(selected: List[tk.Ticket], config: Dict[str, Any], issues: List[Issue]) -> None:
    """Warnings about tickets that will get in each other's way: one file written by a chain, one container shared.

    Seen in a pilot: five tickets of a phase each extended one production file, which grew to 1,266
    lines; each read all of it, the five took half the phase's input, and they ran one at a time
    whatever `parallel.jobs` said. And two tickets rebuilt the same image tag from their own
    worktrees until a pattern for them was added to `parallel.exclusive` by hand.
    """
    by_phase: Dict[int, Dict[str, List[str]]] = {}
    open_files: Set[Tuple[int, str]] = set()
    for ticket in selected:
        if ticket.mode != "hitl":
            for path in ticket.writes:
                by_phase.setdefault(ticket.phase, {}).setdefault(path, []).append(ticket.id)
                if ticket.status != "done":
                    open_files.add((ticket.phase, path))
    for phase, files in sorted(by_phase.items()):
        for path, ids in sorted(files.items()):
            # Only while a ticket on the file is still to run: a finished chain can no longer be split,
            # and a lint over every phase of a project would otherwise repeat it for ever.
            if len(ids) >= SAME_FILE_TICKETS and (phase, path) in open_files \
                    and Path(path).suffix.lower() not in _DOCUMENT_SUFFIXES:
                issues.append(Issue(WARN, f".tickets/phase-{phase:02d}", (
                    f"`{path}` is written by {len(ids)} tickets ({', '.join(ids)}): each reads all of it, and they run one "
                    "after the other. Where the file can be split, give each variant its own file over a shared part, "
                    "in the plan step first")))
    parallel = config.get("parallel") or {}
    if int(parallel.get("jobs") or 1) > 1:
        patterns = [str(pattern) for pattern in parallel.get("exclusive") or []]
        loose = [ticket.id for ticket in selected if ticket.status != "done" and ticket.mode != "hitl"
                 and SHARED_RESOURCE.search(ticket.verify)
                 and not any(fnmatch.fnmatch(ticket.verify, pattern) for pattern in patterns)]
        if len(loose) >= 2:
            issues.append(Issue(WARN, ".devpipe/config.json", (
                f"{len(loose)} tickets run docker in `verify` ({', '.join(loose[:6])}{' …' if len(loose) > 6 else ''}) and no "
                f"`parallel.exclusive` pattern covers them: with parallel.jobs {parallel.get('jobs')} two may run at once "
                "and share an image tag, a container name or a host port")))


def _red_verify(ticket: tk.Ticket, config: Dict[str, Any], where: str, issues: List[Issue]) -> None:
    """`red_verify`, a narrower command for the red check: readable by the shell, and asked for under a whole suite.

    Seen in a pilot: with `whole_suite` in force a ticket's verify is a module's whole test task, and
    the red check ran all of it with the implementation removed, 1,100 to 1,300 tests to learn that
    a handful fail. The task filtered to the ticket's own tests says the same in seconds.
    """
    if ticket.red_verify.strip():
        problem = shell_syntax(ticket.red_verify)
        if problem:
            issues.append(Issue(ERROR, where, f"the shell cannot parse `red_verify`: {problem}"))
        if not ticket.red_check:
            issues.append(Issue(WARN, where, "red_verify is used by the red check only, and this ticket has red_check: false"))
        return
    if not ticket.red_check:
        return
    for prefix, task in (config.get("whole_suite") or {}).items():
        if any(path.startswith(str(prefix)) for path in ticket.writes) and str(task) in ticket.verify:
            issues.append(Issue(WARN, where, f"the red check will run `{task}` whole to see this ticket's tests fail; name "
                                             f"them in `red_verify` (`{task}` filtered to the ticket's own test classes), "
                                             "which the runner first sees pass with the implementation in place"))
            return


def lint_tickets(root: Path, config: Dict[str, Any], phase: Optional[int] = None,
                 counter: Optional[tokens.Counter] = None) -> List[Issue]:
    """Check tickets: header, sizes, blocking graph, read budget, plan coverage."""
    issues: List[Issue] = []
    limits = config["limits"]
    counter = counter or tokens.Counter(config.get("tokens") or {})
    paths = sorted((root / tk.TICKET_DIR).glob("phase-*/ticket-*.md"))
    loaded: List[tk.Ticket] = []
    for path in paths:
        try:
            loaded.append(tk.load(path))
        except tk.TicketError as error:
            issues.append(Issue(ERROR, str(path.relative_to(root)), str(error)))
    by_id = {ticket.id: ticket for ticket in loaded}
    if len(by_id) != len(loaded):
        issues.append(Issue(ERROR, ".tickets", "two tickets share one id"))
    by_number: Dict[Tuple[int, int], str] = {}
    for ticket in loaded:
        twin = by_number.setdefault((ticket.phase, ticket.number), ticket.id)
        if twin != ticket.id:
            issues.append(Issue(ERROR, ".tickets", f"{twin} and {ticket.id} are the same ticket number written two ways"))
    selected = [ticket for ticket in loaded if phase is None or ticket.phase == phase]
    if phase is not None and not selected:
        issues.append(Issue(ERROR, f".tickets/phase-{phase:02d}", "no ticket found for this phase"))
    graph = {ticket.id: ticket.blocked_by for ticket in loaded}
    cycle = _cycle(graph)
    if cycle:
        issues.append(Issue(ERROR, ".tickets", "blocking cycle: " + " -> ".join(cycle)))
    tracked = tracked_files(root)
    produced: Dict[str, List[str]] = {}
    for ticket in loaded:
        for path in ticket.writes + ticket.tests:
            produced.setdefault(path, []).append(ticket.id)
    for ticket in selected:
        where = str(ticket.path.relative_to(root))
        expected = ticket.file_name
        if not where.endswith(expected):
            issues.append(Issue(ERROR, where, f"id {ticket.id} belongs in {expected}"))
        for key in ("title", "plan_ref"):
            if not str(ticket.meta.get(key, "")).strip():
                issues.append(Issue(ERROR, where, f"'{key}' is missing"))
        if ticket.status not in tk.STATUSES:
            issues.append(Issue(ERROR, where, f"status {ticket.status!r} must be one of {', '.join(tk.STATUSES)}"))
        if ticket.mode not in tk.MODES:
            issues.append(Issue(ERROR, where, f"mode {ticket.mode!r} must be afk or hitl"))
        if ticket.host not in tk.HOSTS:
            issues.append(Issue(ERROR, where, f"host {ticket.host!r} must be any, linux or mac"))
        for blocker in ticket.blocked_by:
            if blocker not in by_id:
                issues.append(Issue(ERROR, where, f"blocked_by names unknown ticket {blocker}"))
        body_sections = _sections(ticket.body)
        for name in TICKET_SECTIONS:
            if name not in body_sections:
                issues.append(Issue(ERROR, where, f"section '## {name}' is missing"))
        if "- [ ]" not in body_sections.get("Acceptance", "") and "- [x]" not in body_sections.get("Acceptance", ""):
            issues.append(Issue(ERROR, where, "Acceptance needs at least one '- [ ]' line"))
        _placeholders(ticket.body, where, issues)
        size, _exact = counter.count(ticket.path.read_text(encoding="utf-8"))
        if size > int(limits.get("ticket_tokens", 1200)):
            issues.append(Issue(ERROR, where, f"the ticket itself is {size} tokens; the limit is "
                                              f"{limits.get('ticket_tokens', 1200)} (limits.ticket_tokens)"))
        if ticket.mode == "hitl":
            continue
        if not ticket.verify.strip():
            issues.append(Issue(ERROR, where, "'verify' is missing; it is the command whose exit code decides pass or fail"))
        if not ticket.writes and not ticket.tests:
            issues.append(Issue(ERROR, where, "the ticket writes nothing; list its file under 'writes' or 'tests'"))
        if len(ticket.writes) > int(limits["max_writes"]):
            issues.append(Issue(ERROR, where, f"{len(ticket.writes)} files under 'writes'; the limit is {limits['max_writes']}: split the ticket"))
        if len(ticket.tests) > int(limits["max_tests"]):
            issues.append(Issue(ERROR, where, f"{len(ticket.tests)} files under 'tests'; the limit is {limits['max_tests']}: split the ticket"))
        if ticket.meta.get("alone") not in (None, True, False):
            issues.append(Issue(ERROR, where, f"alone is {ticket.meta.get('alone')!r}; it must be true or false"))
        if ticket.red_check and not (ticket.writes and ticket.tests):
            issues.append(Issue(ERROR, where, "red_check needs both a 'writes' file and a 'tests' file; set red_check: false otherwise"))
        for path in ticket.writes + ticket.tests:
            if Path(path).is_absolute() or ".." in Path(path).parts:
                issues.append(Issue(ERROR, where, f"path {path!r} must be relative and inside the repository"))
        if ticket.status == "done":
            # The read manifest is what an agent is given when the ticket runs. A done ticket does
            # not run again, and the files it read keep growing as later tickets extend them.
            continue
        _package_dependencies(ticket, tracked, graph, produced, where, issues)
        _acceptance_owns_its_files(ticket, tracked, where, issues)
        problem = shell_syntax(ticket.verify)
        if problem:
            issues.append(Issue(ERROR, where, f"the shell cannot parse `verify`: {problem}. The runner gives the command to "
                                              "`sh -c` exactly as it stands between the header's quotes, so a backslash "
                                              "before a quote stays in it and an apostrophe opens a quote"))
        if ticket.red_check:
            # The red check removes the ticket's file and expects verify to fail. A file the
            # project lets a build write comes straight back, so the check proves nothing.
            for path in ticket.writes:
                if any(fnmatch.fnmatch(path, str(pattern)) for pattern in config.get("scope_allow") or []):
                    issues.append(Issue(ERROR, where, f"red_check cannot judge `{path}`: it matches scope_allow, the "
                                                      "patterns for files a build writes; set red_check: false"))
            _red_check_mixes_documents(ticket, where, issues)
        if "\\\\" in ticket.verify:
            # Seen in a pilot: a draft wrote `'^8\\. …'`. The header keeps both backslashes, so grep
            # looked for a literal backslash and the ticket could never pass.
            issues.append(Issue(WARN, where, "`verify` holds `\\\\`: the header's quotes are stripped and nothing else, "
                                             "so `sh -c` receives both backslashes. In a grep pattern write `[.]`, `[|]` "
                                             "or `[(]` for a literal character instead"))
        _whole_suite(ticket, config, where, issues)
        _red_verify(ticket, config, where, issues)
        total = 0
        for entry in ticket.read:
            path = str(entry.get("path", ""))
            text, problem = read_entry_text(root, entry)
            if text is None:
                # A ticket that runs first creates the file: one with a lower number, or one this
                # ticket waits for (a feature's ticket has a higher number and still runs first).
                first = [maker for maker in produced.get(path, []) if maker != ticket.id and (
                    (by_id[maker].phase, by_id[maker].number) < (ticket.phase, ticket.number)
                    or waits_for(ticket.id, maker, graph))]
                if problem == "file does not exist" and first:
                    # Budget it at the size cap for a new file.
                    total += int(limits["write_lines"]) * 12
                else:
                    issues.append(Issue(ERROR, where, f"read entry {path!r}: {problem}"))
                continue
            size, _exact = counter.count(text)
            total += size
        if total > int(limits["read_tokens"]):
            issues.append(Issue(ERROR, where, f"read manifest is {total} tokens; the limit is {limits['read_tokens']}: "
                                              "narrow the line ranges or split the ticket"))
    if not counter.exact:
        issues.append(Issue(WARN, ".tickets", f"token sizes are estimates ({counter.reason}); "
                                              "run the lint again with the model server up for exact counts"))
    _refined_tests(selected, by_id, root, issues)
    _shared_files_and_resources(selected, config, issues)
    plan_path = root / "DEV_PLAN.md"
    if phase is not None and plan_path.is_file():
        section = plan_phases(plan_path.read_text(encoding="utf-8")).get(phase, "")
        if re.search(r"^\*\*Exit demo:\*\*\s*\S", section, flags=re.MULTILINE) and selected \
                and not any(ticket.mode == "hitl" for ticket in selected):
            # Seen in a pilot: a phase whose plan had an exit demo got no manual ticket for it. The runner
            # never stopped to hand it over, the gate before it never ran, and the phase was merged undemonstrated.
            issues.append(Issue(ERROR, f".tickets/phase-{phase:02d}",
                                "the plan gives this phase an exit demo and no ticket is `mode: hitl`, so nobody is handed "
                                "the demo: write it as the phase's last ticket, blocked by every other one"))
        steps = plan_steps(plan_path.read_text(encoding="utf-8")).get(phase, [])
        refs = " ".join(str(ticket.meta.get("plan_ref", "")) for ticket in selected)
        for step_id, title, _block in steps:
            if not re.search(rf"(?<![\d.]){re.escape(step_id)}(?![\d])", refs):
                issues.append(Issue(ERROR, f".tickets/phase-{phase:02d}", f"plan step {step_id} ({title}) has no ticket"))
    return issues


def lint_agents(root: Path, config: Dict[str, Any]) -> List[Issue]:
    """Check the generated agent trio for each tier present in the project."""
    issues: List[Issue] = []
    names = config.get("agents") or {}
    for role in ("engineer", "reviewer", "diagnostic"):
        if not names.get(role):
            issues.append(Issue(ERROR, ".devpipe/config.json", f"agents.{role} is not set"))
    for tier, folder in AGENT_DIRS.items():
        present = (root / folder).is_dir()
        if not present:
            if config.get("adapter") == tier:
                issues.append(Issue(ERROR, folder, f"missing, but the configured adapter is {tier}"))
            continue
        for role in ("engineer", "reviewer", "diagnostic"):
            if not names.get(role):
                continue
            where = f"{folder}/{names[role]}.md"
            text = _read(root / where, issues)
            if text is None:
                continue
            try:
                meta, body = fm.load(text)
            except fm.FrontMatterError as error:
                issues.append(Issue(ERROR, where, str(error)))
                continue
            words = len(body.split())
            budget = WORD_BUDGET[tier][role]
            if words > budget and WORD_BUDGET_IS_A_LIMIT[tier]:
                issues.append(Issue(ERROR, where, f"body is {words} words; the {tier} budget for the {role} is {budget}"))
            elif words > budget:
                issues.append(Issue(WARN, where, f"body is {words} words; the {tier} guide for the {role} is {budget}. "
                                                 "It is sent with every call of this agent: a cost on every call, not a limit"))
            for token in ("TICKET", "STEP"):
                if token not in body:
                    issues.append(Issue(ERROR, where, f"body never mentions {token}; the runner's prompt uses that key"))
            _placeholders(body, where, issues, blanks_only=True)
            if not str(meta.get("description", "")).strip():
                issues.append(Issue(ERROR, where, "'description' is missing"))
            if tier == "opencode":
                _lint_opencode_agent(meta, role, where, issues)
            else:
                _lint_claude_agent(meta, role, names[role], where, issues)
    return issues


def _lint_opencode_agent(meta: Dict[str, Any], role: str, where: str, issues: List[Issue]) -> None:
    rules = meta.get("permissions")
    if not isinstance(rules, list) or not rules or not all(isinstance(rule, dict) for rule in rules):
        issues.append(Issue(ERROR, where, "'permissions' must be a list of {action, resource, effect} rules"))
        return
    first = rules[0]
    if (first.get("action"), first.get("resource"), first.get("effect")) != ("*", "*", "deny"):
        issues.append(Issue(ERROR, where, "the first permission rule must deny everything: {action: \"*\", resource: \"*\", effect: deny}"))
    for rule in rules[1:]:
        action, effect = str(rule.get("action")), str(rule.get("effect"))
        if effect not in ("allow", "deny"):
            issues.append(Issue(ERROR, where, f"effect {effect!r} must be allow or deny; 'ask' cannot be answered in an unattended run"))
        if effect == "allow" and action in ("skill", "websearch", "webfetch", "task", "browser", "question", "*"):
            issues.append(Issue(ERROR, where, f"'{action}' must not be allowed for a pipeline agent"))
        if effect == "allow" and action == "edit" and role != "engineer":
            issues.append(Issue(ERROR, where, f"the {role} must not be allowed to edit files"))
    if not isinstance(meta.get("steps"), int):
        issues.append(Issue(ERROR, where, "'steps' (the iteration cap) is missing"))
    if meta.get("mode") not in ("primary", "all"):
        issues.append(Issue(ERROR, where, "'mode' must be primary or all so `opencode run --agent` can start it"))


def _lint_claude_agent(meta: Dict[str, Any], role: str, name: str, where: str, issues: List[Issue]) -> None:
    if meta.get("name") != name:
        issues.append(Issue(ERROR, where, f"'name' must be {name}"))
    tools = meta.get("tools")
    listed = [part.strip() for part in tools.split(",")] if isinstance(tools, str) else [str(part) for part in tools or []]
    if not listed:
        issues.append(Issue(ERROR, where, "'tools' is missing; a pipeline agent names its tools explicitly"))
    if role != "engineer" and any(tool in ("Edit", "Write", "NotebookEdit") for tool in listed):
        issues.append(Issue(ERROR, where, f"the {role} must not have Edit or Write"))
    for tool in listed:
        if tool in ("WebFetch", "WebSearch", "Agent", "Task", "Skill"):
            issues.append(Issue(ERROR, where, f"'{tool}' must not be given to a pipeline agent"))
