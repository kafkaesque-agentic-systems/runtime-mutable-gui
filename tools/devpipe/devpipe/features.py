"""Feature records (`design/features/F-NNN-slug.md`).

Purpose: let a feature that turns up in the middle of development enter the
pipeline through the same checked artifacts as everything else. A record holds
the mini design; once accepted it is folded into the specification, the plan
and the tickets, and the lint here checks that the fold is complete: the
requirements exist, the plan steps carry the feature's tag, every invariant was
considered, every ticket built against a changed requirement is accounted for,
and every unfinished ticket that shares a file with the feature is ordered
against it.
Dependencies: fm, lint, tickets, gitutil.
Side effects: `new` and `file_inbox` create record files; `inbox_add` appends to
a gitignored file under `.tickets/.work/`; `close_finished` rewrites one header
line. Nothing here commits.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from . import fm, gitutil as git, lint, tickets as tk

FEATURE_DIR = "design/features"
INBOX_FILE = "feature-inbox.jsonl"
ID_PATTERN = re.compile(r"^F-(\d{3})$")
STATUSES = ("PROPOSED", "ACCEPTED", "DONE", "DROPPED")
PLACEMENTS = ("none", "now", "later", "rework")
DESIGNED_SECTIONS = ["Behaviour", "Acceptance", "Out of scope", "Invariants", "Rework", "Placement"]


class FeatureError(ValueError):
    """A feature file cannot be read as a feature record."""


@dataclass
class Feature:
    """One record; `meta` keeps the raw header for the lint."""

    path: Path
    meta: Dict[str, Any]
    body: str
    id: str = ""
    title: str = ""
    status: str = "PROPOSED"
    placement: str = "none"
    requirements: List[str] = field(default_factory=list)
    changes: List[str] = field(default_factory=list)
    serves: List[str] = field(default_factory=list)
    touches: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)

    @property
    def scheduled(self) -> bool:
        """True once the feature is part of the plan."""
        return self.status in ("ACCEPTED", "DONE")


def _strings(value: Any) -> List[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def load(path: Path) -> Feature:
    """Read one record. Raises FeatureError when the header or id is unusable."""
    try:
        meta, body = fm.load(path.read_text(encoding="utf-8"))
    except (OSError, fm.FrontMatterError) as error:
        raise FeatureError(f"{path}: {error}") from error
    feature_id = str(meta.get("id", ""))
    if not ID_PATTERN.match(feature_id):
        raise FeatureError(f"{path}: id {feature_id!r} does not look like F-003")
    return Feature(
        path=path, meta=meta, body=body, id=feature_id, title=str(meta.get("title", "")),
        status=str(meta.get("status", "PROPOSED")), placement=str(meta.get("placement", "none")),
        requirements=_strings(meta.get("requirements")), changes=_strings(meta.get("changes")),
        serves=_strings(meta.get("serves")), touches=_strings(meta.get("touches")),
        steps=_strings(meta.get("steps")),
    )


def paths(root: Path) -> List[Path]:
    return sorted((root / FEATURE_DIR).glob("F-*.md"))


def load_all(root: Path) -> List[Feature]:
    """Every readable record, in id order. Unreadable files are the lint's business."""
    found = []
    for path in paths(root):
        try:
            found.append(load(path))
        except FeatureError:
            continue
    return sorted(found, key=lambda feature: feature.id)


# ------------------------------------------------------------------ creating

def invariants(root: Path) -> List[Tuple[str, str]]:
    """(id, text) of each invariant in design/ARCHITECTURE.md."""
    path = root / "design" / "ARCHITECTURE.md"
    if not path.is_file():
        return []
    section = lint._sections(path.read_text(encoding="utf-8")).get("Invariants", "")
    found: Dict[str, str] = {}
    for line in section.splitlines():
        match = re.search(r"\b(I-\d{2})\b\**\s*(.*)", line)
        if match:
            found.setdefault(match.group(1), match.group(2).strip())
    return sorted(found.items())


def _short_title(idea: str) -> str:
    words = re.sub(r"\s+", " ", idea).strip().split(" ")
    title = " ".join(words[:8])
    return (title[:60].rstrip() or "feature").rstrip(".,;:")


def _slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "feature"


def new(root: Path, idea: str, title: str = "") -> Feature:
    """Create the next record from the template with the idea filled in; status PROPOSED."""
    # File names, not headers, so a record with a broken header still keeps its number.
    numbers = [int(match.group(1)) for match in (re.match(r"F-(\d{3})", path.name) for path in paths(root)) if match]
    feature_id = f"F-{max(numbers, default=0) + 1:03d}"
    title = re.sub(r"\s+", " ", title).strip() or _short_title(idea)
    template = (Path(__file__).resolve().parent.parent / "templates" / "feature.md").read_text(encoding="utf-8")
    lines = [f"- {name} ({text[:90]}): <<not affected, or how the feature keeps it>>" for name, text in invariants(root)]
    text = (template.replace("{{id}}", feature_id)
            .replace("{{title}}", title.replace('"', "'"))
            .replace("{{idea}}", idea.strip())
            .replace("{{invariants}}", "\n".join(lines) or "None are defined in design/ARCHITECTURE.md."))
    path = root / FEATURE_DIR / f"{feature_id}-{_slug(title)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return load(path)


def _inbox(root: Path) -> Path:
    return root / tk.TICKET_DIR / tk.WORK_DIR / INBOX_FILE


def inbox_add(root: Path, idea: str, title: str = "") -> int:
    """Hold an idea outside the tracked tree while a run is active; return how many wait."""
    path = _inbox(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"idea": idea.strip(), "title": title.strip()}) + "\n")
    return len(inbox_read(root))


def inbox_read(root: Path) -> List[Dict[str, str]]:
    try:
        lines = _inbox(root).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and str(entry.get("idea", "")).strip():
            entries.append({"idea": str(entry["idea"]), "title": str(entry.get("title", ""))})
    return entries


def file_inbox(root: Path) -> List[Feature]:
    """Turn every held idea into a record and empty the inbox. Call only when no run is active."""
    created = [new(root, entry["idea"], entry["title"]) for entry in inbox_read(root)]
    _inbox(root).unlink(missing_ok=True)
    return created


# ----------------------------------------------------------- reading the project

def _plan(root: Path) -> Dict[int, List[Tuple[str, str, str]]]:
    path = root / "DEV_PLAN.md"
    return lint.plan_steps(path.read_text(encoding="utf-8")) if path.is_file() else {}


def step_of(ticket: tk.Ticket) -> str:
    """The plan step id ('2.7') a ticket's `plan_ref` names, or an empty string."""
    match = re.search(r"(?<![\d.])(\d+\.\d+)(?!\d)", str(ticket.meta.get("plan_ref", "")))
    return match.group(1) if match else ""


def cited(ticket: tk.Ticket) -> Set[str]:
    """Requirement ids in a ticket's `requirement:` field."""
    return set(re.findall(r"R-\d{3}", str(ticket.meta.get("requirement", ""))))


def used_paths(ticket: tk.Ticket) -> Dict[str, str]:
    """{path: 'writes' | 'reads'} for every file a ticket names."""
    used = {str(entry.get("path", "")): "reads" for entry in ticket.read}
    used.update({path: "writes" for path in ticket.writes + ticket.tests})
    used.pop("", None)
    return used


def tickets_of(feature: Feature, everything: List[tk.Ticket]) -> List[tk.Ticket]:
    return [ticket for ticket in everything if str(ticket.meta.get("feature", "")) == feature.id]


def _phase_state(root: Path, everything: List[tk.Ticket]) -> Tuple[List[Tuple[int, int, int]], int, int]:
    """([(phase, done, total)], phase in progress or 0, first planned phase without tickets or 0)."""
    rows = []
    for phase in sorted({ticket.phase for ticket in everything}):
        in_phase = [ticket for ticket in everything if ticket.phase == phase]
        rows.append((phase, sum(1 for ticket in in_phase if ticket.status == "done"), len(in_phase)))
    working = next((phase for phase, done, total in rows if done < total), 0)
    ticketed = {phase for phase, _done, _total in rows}
    unstarted = next((phase for phase in sorted(_plan(root)) if phase > 0 and phase not in ticketed), 0)
    return rows, working, unstarted


def work_branch(root: Path) -> str:
    """Branch that holds the phase in progress, when that branch exists; else an empty string.

    A record committed anywhere else would be missing from the branch the runner works on.
    """
    try:
        everything = tk.load_all(root)
    except tk.TicketError:
        return ""
    _rows, working, _unstarted = _phase_state(root, everything)
    name = f"phase/{working:02d}"
    return name if working and git.is_repo(root) and git.branch_exists(root, name) else ""


def _next_free(root: Path, everything: List[tk.Ticket], phases: List[int]) -> str:
    """The first unused requirement and decision ids, and per phase the first unused step and ticket."""
    parts = []
    for label, name, pattern in (("requirement", "SPECIFICATION.md", r"^### R-(\d{3})\b"),
                                 ("decision", "DECISIONS.md", r"^## D-(\d{2})\b")):
        path = root / "design" / name
        found = [int(number) for number in re.findall(pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE)] \
            if path.is_file() else []
        width = 3 if label == "requirement" else 2
        parts.append(f"{label} {'R' if label == 'requirement' else 'D'}-{max(found, default=0) + 1:0{width}d}")
    for phase in phases:
        numbers = [int(step_id.split(".")[1]) for step_id, _title, _block in _plan(root).get(phase, [])]
        mine = [ticket for ticket in everything if ticket.phase == phase]
        # The same number of digits the phase's tickets already use.
        width = max([len(ticket.id.split("-T")[1]) for ticket in mine] or [2])
        parts.append(f"phase {phase}: step {phase}.{max(numbers, default=0) + 1}, "
                     f"ticket P{phase:02d}-T{max([ticket.number for ticket in mine] or [0]) + 1:0{width}d}")
    return " · ".join(parts)


def impact(root: Path, touches: List[str], changes: List[str], feature: Optional[Feature] = None,
           run_note: str = "") -> str:
    """What a feature that uses `touches` and rewrites `changes` meets in the project, as text.

    Everything comes from ticket headers and the plan, so the same question gets
    the same answer whoever asks it.
    """
    everything = tk.load_all(root)
    own = {ticket.id for ticket in tickets_of(feature, everything)} if feature else set()
    others = [ticket for ticket in everything if ticket.id not in own]
    touched, changed = set(touches), set(changes)
    wrote = [(ticket, sorted(touched & set(ticket.writes))) for ticket in others
             if ticket.status == "done" and touched & set(ticket.writes)]
    built = [(ticket, sorted(changed & cited(ticket))) for ticket in others
             if ticket.status == "done" and changed & cited(ticket)]
    waiting_files = [(ticket, sorted((path, how) for path, how in used_paths(ticket).items() if path in touched))
                     for ticket in others if ticket.status != "done" and touched & set(used_paths(ticket))]
    waiting_reqs = [(ticket, sorted(changed & cited(ticket))) for ticket in others
                    if ticket.status != "done" and changed & cited(ticket)]
    rows, working, unstarted = _phase_state(root, everything)

    lines = [f"Feature {feature.id} — {feature.title}" if feature else "Feature (not filed yet)",
             "touches: " + (", ".join(sorted(touched)) or "(none named)"),
             "changes: " + (", ".join(sorted(changed)) or "(none named)"), ""]

    def block(title: str, entries: List[str]) -> None:
        lines.append(title)
        lines.extend(f"  {entry}" for entry in entries) if entries else lines.append("  none")

    block("Finished tickets that wrote these files (the feature modifies their code):",
          [f"{ticket.id}  {', '.join(files)}  {ticket.title}" for ticket, files in wrote])
    block("Finished tickets built against the changed requirements (each needs a line under '## Rework'):",
          [f"{ticket.id}  {', '.join(ids)}  {ticket.title}" for ticket, ids in built])
    block("Unfinished tickets that use these files (each must be ordered against the feature's tickets):",
          [f"{ticket.id}  {', '.join(f'{how} {path}' for path, how in files)}  {ticket.status}  {ticket.title}"
           for ticket, files in waiting_files])
    block("Unfinished tickets that cite the changed requirements (each needs a line under '## Rework'):",
          [f"{ticket.id}  {', '.join(ids)}  {ticket.status}  {ticket.title}" for ticket, ids in waiting_reqs])
    lines.append("Phases:")
    for phase, done, total in rows:
        lines.append(f"  {phase}  {done}/{total} tickets done" + ("   <- in progress" if phase == working else ""))
    ticketed = {phase for phase, _done, _total in rows}
    for phase in sorted(_plan(root)):
        if phase > 0 and phase not in ticketed:
            lines.append(f"  {phase}  in the plan, no tickets yet")
    if not rows and not _plan(root):
        lines.append("  no plan and no tickets yet")
    if run_note:
        lines.append(f"Run: {run_note}")
    branch = work_branch(root)
    if branch and git.branch(root) != branch:
        lines.append(f"Branch: phase {working}'s work is on `{branch}` and this is `{git.branch(root)}`; "
                     f"`git switch {branch}` before changing anything")

    in_flight = [ticket for ticket, _files in waiting_files] + [ticket for ticket, _ids in waiting_reqs]
    if not touched and not changed:
        target, suggestion = working or unstarted, "none yet: name the files it touches and the requirements it changes first"
    elif in_flight:
        target = min(ticket.phase for ticket in in_flight)
        names = ", ".join(sorted({ticket.id for ticket in in_flight}))
        suggestion = f"now, in phase {target}: {names} not built yet and depend on what the feature changes"
    elif wrote or built:
        target = working or unstarted
        names = ", ".join(sorted({ticket.id for ticket, _x in wrote + built}))
        where = f"in phase {target}" if target else "in a new phase"
        suggestion = f"rework, {where}: it changes what {names} already built, and nothing unfinished depends on it"
    else:
        target = unstarted or working
        where = f"in phase {target}" if target else "in a new phase"
        suggestion = f"later, {where}: nothing built or queued depends on it"
    lines.append(f"Suggested placement: {suggestion}")
    lines.append(f"Next free: {_next_free(root, everything, sorted({working, unstarted, target} - {0}))}")
    return "\n".join(lines)


# ------------------------------------------------------------ status and listing

def close_finished(root: Path) -> List[str]:
    """Set ACCEPTED records to DONE when every step has a ticket and all their tickets are done."""
    try:
        everything = tk.load_all(root)
    except tk.TicketError:
        return []
    closed = []
    for feature in load_all(root):
        mine = tickets_of(feature, everything)
        covered = {step_of(ticket) for ticket in mine}
        if feature.status == "ACCEPTED" and feature.steps and set(feature.steps) <= covered \
                and all(ticket.status == "done" for ticket in mine):
            feature.path.write_text(fm.set_scalar(feature.path.read_text(encoding="utf-8"), "status", "DONE"),
                                    encoding="utf-8")
            closed.append(feature.id)
    return closed


def progress(feature: Feature, everything: List[tk.Ticket]) -> str:
    mine = tickets_of(feature, everything)
    if not feature.scheduled:
        return ""
    if not mine:
        return f"steps {', '.join(feature.steps) or '?'}, no tickets yet"
    return f"{sum(1 for ticket in mine if ticket.status == 'done')}/{len(mine)} tickets done"


def listing(root: Path) -> List[str]:
    """One line per record, then the inbox count."""
    try:
        everything = tk.load_all(root)
    except tk.TicketError:
        everything = []
    lines = [f"{feature.id}  {feature.status:8} {feature.placement:6} {feature.title}"
             + (f"  ({progress(feature, everything)})" if progress(feature, everything) else "")
             for feature in load_all(root)]
    waiting = len(inbox_read(root))
    if waiting:
        lines.append(f"inbox: {waiting} idea(s) captured during a run; they are filed the next time "
                     "`devpipe feature list` runs with no run active")
    return lines or ["no features"]


# Ids named per status in the one-line summary; the rest are counted, never dropped silently.
SUMMARY_IDS = 6


def summary(root: Path) -> str:
    """A one-line count for `devpipe status` and HANDOFF.md; empty when there is nothing to say."""
    counts: Dict[str, List[str]] = {}
    for feature in load_all(root):
        counts.setdefault(feature.status, []).append(feature.id)
    parts = [f"{len(ids)} {status.lower()} ({', '.join(ids[:SUMMARY_IDS])}"
             f"{f' and {len(ids) - SUMMARY_IDS} more' if len(ids) > SUMMARY_IDS else ''})"
             for status, ids in counts.items() if status in ("PROPOSED", "ACCEPTED")]
    waiting = len(inbox_read(root))
    if waiting:
        parts.append(f"{waiting} in the inbox")
    return ", ".join(parts)


# ------------------------------------------------------------------------- lint

def lint_features(root: Path, config: Dict[str, Any]) -> List[lint.Issue]:
    """Check every record, and that plan steps and tickets agree with the records."""
    issues: List[lint.Issue] = []

    def error(where: str, message: str) -> None:
        issues.append(lint.Issue(lint.ERROR, where, message))

    loaded: List[Feature] = []
    for path in paths(root):
        where = str(path.relative_to(root))
        try:
            feature = load(path)
        except FeatureError as problem:
            error(where, str(problem).split(": ", 1)[-1])
            continue
        if not path.name.startswith(feature.id + "-"):
            error(where, f"id {feature.id} belongs in a file named {feature.id}-<slug>.md")
        if any(other.id == feature.id for other in loaded):
            error(where, f"{feature.id} is defined twice")
        loaded.append(feature)
    by_id = {feature.id: feature for feature in loaded}

    plan = _plan(root)
    step_blocks = {step_id: block for steps in plan.values() for step_id, _title, block in steps}
    tagged: Dict[str, str] = {}
    for step_id, block in step_blocks.items():
        match = re.search(r"^- Feature:\s*(F-\d{3})\b", block, flags=re.MULTILINE)
        if match:
            tagged[step_id] = match.group(1)
    for step_id, feature_id in sorted(tagged.items()):
        feature = by_id.get(feature_id)
        if feature is None or not feature.scheduled:
            error(f"DEV_PLAN.md step {step_id}", f"is tagged {feature_id}, which is not an accepted feature record")
        elif step_id not in feature.steps:
            error(f"DEV_PLAN.md step {step_id}", f"is tagged {feature_id}, but that record's `steps` does not list it")

    try:
        everything = tk.load_all(root)
    except tk.TicketError:
        everything = []  # `lint tickets` reports the unreadable ticket
    graph = {ticket.id: ticket.blocked_by for ticket in everything}
    for ticket in everything:
        where = str(ticket.path.relative_to(root))
        named = str(ticket.meta.get("feature", ""))
        wanted = tagged.get(step_of(ticket), "")
        if named and (named not in by_id or not by_id[named].scheduled):
            error(where, f"`feature: {named}` is not an accepted feature record")
        elif named and step_of(ticket) not in by_id[named].steps:
            error(where, f"`feature: {named}`, but plan step {step_of(ticket) or '?'} is not one of that feature's steps")
        elif wanted and named != wanted:
            error(where, f"plan step {step_of(ticket)} belongs to {wanted}; add `feature: {wanted}` to the header")

    spec_path = root / "design" / "SPECIFICATION.md"
    defined = set(lint.requirement_ids(spec_path.read_text(encoding="utf-8"))) if spec_path.is_file() else set()
    known_invariants = [name for name, _text in invariants(root)]
    limit = int(config["limits"].get("feature_max_steps", 5))

    for feature in loaded:
        where = str(feature.path.relative_to(root))
        sections = lint._sections(feature.body)
        if feature.status not in STATUSES:
            error(where, f"status {feature.status!r} must be one of {', '.join(STATUSES)}")
        if feature.placement not in PLACEMENTS:
            error(where, f"placement {feature.placement!r} must be one of {', '.join(PLACEMENTS)}")
        if not str(feature.title).strip():
            error(where, "'title' is missing")
        if lint._is_empty_section(sections.get("Idea", "")):
            error(where, "section '## Idea' is missing or empty; it holds the owner's words")
        if not feature.scheduled:
            continue

        # Blanks only: the Idea section holds the owner's words, which may say "TODO".
        lint._placeholders(feature.body, where, issues, blanks_only=True)
        for name in DESIGNED_SECTIONS:
            if not sections.get(name, "").strip():
                error(where, f"section '## {name}' is missing or empty (write 'None.' when there is nothing)")
        if feature.placement == "none":
            error(where, "an accepted feature needs `placement: now`, `later` or `rework`")
        mine = set(feature.requirements) | set(feature.changes) | set(feature.serves)
        if not mine:
            error(where, "names no requirement; fill `requirements`, `changes` or `serves`")
        for name in sorted(mine - defined):
            error(where, f"{name} is not defined in design/SPECIFICATION.md")
        if not feature.steps:
            error(where, "`steps` is empty; an accepted feature has at least one plan step")
        if len(feature.steps) > limit:
            error(where, f"{len(feature.steps)} plan steps; over {limit} is a plan revision, not a feature: "
                         "split it, or take it through the dev-plan stage")
        covered: Set[str] = set()
        for step_id in feature.steps:
            block = step_blocks.get(step_id)
            if block is None:
                error(where, f"step {step_id} is not in DEV_PLAN.md")
                continue
            if tagged.get(step_id) != feature.id:
                error(where, f"plan step {step_id} lacks the line '- Feature: {feature.id}'")
            field_text = re.search(r"^- Requirements:(.*)$", block, flags=re.MULTILINE)
            named_here = set(re.findall(r"R-\d{3}", field_text.group(1))) if field_text else set()
            if not named_here & mine:
                error(where, f"plan step {step_id} cites none of this feature's requirements")
            covered |= named_here
        for name in sorted(set(feature.requirements) - covered):
            if feature.steps:
                error(where, f"{name} is new with this feature, but none of its steps cites it")
        for name in known_invariants:
            if not re.search(rf"\b{name}\b", sections.get("Invariants", "")):
                error(where, f"'## Invariants' says nothing about {name}; state 'not affected' or how it is kept")

        own = tickets_of(feature, everything)
        own_ids = {ticket.id for ticket in own}
        for ticket in own:
            for path in sorted(set(ticket.writes) - set(feature.touches)):
                error(where, f"its ticket {ticket.id} writes {path}, which `touches` does not list")
        if feature.status == "DONE":
            if not own or any(ticket.status != "done" for ticket in own) \
                    or not set(feature.steps) <= {step_of(ticket) for ticket in own}:
                error(where, "status is DONE, but not every step has a finished ticket")
            continue

        # From here on the feature is ACCEPTED: scheduled, not finished.
        rework = sections.get("Rework", "")
        for ticket in everything:
            hit = sorted(set(feature.changes) & cited(ticket))
            if hit and ticket.id not in own_ids and not re.search(rf"\b{re.escape(ticket.id)}\b", rework):
                state = "was built against" if ticket.status == "done" else "cites"
                error(where, f"{ticket.id} {state} {', '.join(hit)}, which this feature changes; say under "
                             "'## Rework' which step reworks it, or why it needs no change")
        for mine_ticket in own:
            if mine_ticket.status == "done":
                continue
            shared = set(mine_ticket.writes + mine_ticket.tests) & set(feature.touches)
            for other in everything:
                if other.id in own_ids or other.status == "done":
                    continue
                both = sorted(shared & set(used_paths(other)))
                if both and not lint.waits_for(other.id, mine_ticket.id, graph) \
                        and not lint.waits_for(mine_ticket.id, other.id, graph):
                    error(where, f"{other.id} and this feature's {mine_ticket.id} both use {', '.join(both)} and "
                                 "neither waits for the other; add `blocked_by` one way")
    return issues
