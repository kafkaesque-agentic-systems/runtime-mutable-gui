"""Command line for the toolkit: `devpipe <command>`.

Purpose: the one entry point that stage skills, stage agents and the owner
call. Every command is deterministic; none of them calls a model except `run`,
which does so only through an adapter.
Side effects: per command, documented in each handler's help text.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import VERSION, config as cfg, features, gates, gitutil as git, lint, parallel, report, runner, scaffold, tickets as tk, tokens, ui

PROBE_TOOLS = ["git", "python3", "uv", "pip", "node", "npm", "pnpm", "bun", "deno", "cargo", "rustc", "go",
               "java", "gradle", "mvn", "cmake", "ninja", "make", "gcc", "clang", "docker", "podman",
               "psql", "sqlite3", "jq", "rg", "shellcheck"]


def _root() -> Path:
    root = cfg.find_root()
    if root is None:
        sys.exit("devpipe: this folder is not set up; run `devpipe doctor` in the project folder first")
    return root


def _print_issues(issues: List[lint.Issue]) -> int:
    for issue in issues:
        print(issue)
    errors = sum(1 for issue in issues if issue.level == lint.ERROR)
    print(f"lint: {errors} error(s), {len(issues) - errors} warning(s)")
    return 1 if errors else 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = cfg.find_root() or Path.cwd()
    notes = scaffold.doctor(root, fix=not args.check, adapter=args.adapter or "", slug=args.slug or "",
                            refresh=args.command == "sync", busy=bool(_active_run(root)),
                            discard_local=bool(getattr(args, "discard_local", False)))
    for note in notes:
        # A NOTE is something left for the person to do, so it gets no "done:" in front of it.
        print(note if note.startswith("NOTE") else ("needed: " if args.check else "done: ") + note)
    if not notes:
        print(f"devpipe {VERSION}: project is set up ({root})")
    return 1 if args.check and notes else 0


def cmd_lint(args: argparse.Namespace) -> int:
    root = _root()
    config = cfg.load(root)
    issues: List[lint.Issue] = []
    if args.what in ("spec", "all"):
        issues += lint.lint_spec(root, allow_open=args.allow_open)
    if args.what in ("plan", "all"):
        issues += lint.lint_plan(root) + ui.lint_coverage(root)
    if args.what == "ui" or (args.what == "all" and (root / ui.UI_FILE).is_file()):
        issues += ui.lint_ui(root, allow_open=args.allow_open)
    if args.what in ("tickets", "all"):
        issues += lint.lint_tickets(root, config, args.phase)
    if args.what in ("agents", "all"):
        issues += lint.lint_agents(root, config)
    if args.what in ("features", "tickets", "all"):
        # With the tickets too: a run's preflight refuses a ticket for its feature record, and the
        # lint a stage runs before its commit must not pass what the run then refuses.
        issues += features.lint_features(root, config)
    return _print_issues(issues)


# Set for the process a detached run starts, so it does not repeat what its starter already did.
DETACHED_CHILD = "DEVPIPE_DETACHED_CHILD"


def _run_files(root: Path) -> "tuple[Path, Path]":
    """(pid file, log file) of a run; both live in the gitignored work folder."""
    work = root / tk.TICKET_DIR / tk.WORK_DIR
    return work / "run.pid", work / "run.log"


def _active_run(root: Path) -> int:
    """Pid of the run that is active in this project, or 0."""
    pid_file, _log = _run_files(root)
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, 0)
    except (OSError, ValueError):
        return 0
    return pid


def _interrupt(_signal: int, _frame: object) -> None:
    # `devpipe stop` sends SIGTERM; treating it like Ctrl-C lets the runner put
    # the tree back to the pre-ticket commit before it exits.
    raise KeyboardInterrupt


def cmd_run(args: argparse.Namespace) -> int:
    root = _root()
    pid_file, log_file = _run_files(root)
    active = _active_run(root)
    if active and active != os.getpid():
        print(f"devpipe: a run is already active in this project (pid {active}); `devpipe status` shows it")
        return runner.EXIT_OWNER
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    jobs = args.jobs or int((cfg.load(root).get("parallel") or {}).get("jobs") or 1)
    if not os.environ.get(DETACHED_CHILD):
        # A pause request left over from an earlier run is cleared here, before this run exists.
        # The runner must never clear it later: a `pause` sent while the run is still starting
        # up would be wiped, and the run would carry on as if nobody had asked.
        (pid_file.parent / runner.PAUSE_FILE).unlink(missing_ok=True)
    if args.detach:
        command = [sys.executable, str(Path(__file__).resolve().parent.parent / "run.py"), "run", "--phase", str(args.phase)]
        command += ["--jobs", str(jobs)]
        command += ["--continue-on-block"] if args.continue_on_block else []
        command += ["--max-tickets", str(args.max_tickets)] if args.max_tickets else []
        with log_file.open("w", encoding="utf-8") as log:
            # A new session, so the run outlives the terminal or agent that started it.
            child = subprocess.Popen(command, cwd=str(root), stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True,
                                     env={**os.environ, DETACHED_CHILD: "1"})
        pid_file.write_text(str(child.pid))
        print(f"devpipe: phase {args.phase} is running in the background (pid {child.pid})")
        print("devpipe: `devpipe status` shows progress, `devpipe stop` ends it cleanly")
        return 0
    pid_file.write_text(str(os.getpid()))
    signal.signal(signal.SIGTERM, _interrupt)
    try:
        if jobs > 1:
            return parallel.ParallelRunner(root, args.phase, jobs, args.continue_on_block, args.max_tickets).run()
        return runner.Runner(root, args.phase, args.continue_on_block, args.max_tickets).run()
    except runner.Halt as halt:
        print(f"devpipe: {halt}")
        return halt.code
    except (git.GitError, cfg.ConfigError, tk.TicketError) as error:
        print(f"devpipe: {error}")
        return runner.EXIT_INFRA
    except KeyboardInterrupt:
        print("devpipe: interrupted between tickets; nothing was in progress")
        return 130
    finally:
        pid_file.unlink(missing_ok=True)
        (pid_file.parent / runner.PAUSE_FILE).unlink(missing_ok=True)


def cmd_worker(args: argparse.Namespace) -> int:
    """One ticket's attempt in a worktree. Started by `run --jobs`; not meant to be typed.

    Works the ticket in the current folder and leaves the result in the ticket's work
    folder as outcome.json. It records nothing: the coordinator does that on the phase branch.
    """
    root = _root()
    signal.signal(signal.SIGTERM, _interrupt)
    matches = [ticket for ticket in tk.load_all(root) if ticket.id == args.ticket]
    if not matches:
        sys.exit(f"devpipe: no ticket {args.ticket}")
    ticket = matches[0]
    result_file = ticket.work_dir(root) / parallel.OUTCOME_FILE
    result_file.parent.mkdir(parents=True, exist_ok=True)
    worker = runner.Runner(root, args.phase)
    try:
        try:
            outcome = worker.attempt(ticket)
        except KeyboardInterrupt:
            worker._infra(ticket, "stopped")  # saves the work as a patch, restores the tree, raises Halt
            raise
    except runner.Halt as halt:
        result_file.write_text(json.dumps({"kind": "infra", "detail": str(halt)}) + "\n", encoding="utf-8")
        print(f"devpipe: {halt}", flush=True)
        return halt.code
    result_file.write_text(json.dumps(dataclasses.asdict(outcome)) + "\n", encoding="utf-8")
    return 0 if outcome.kind == "done" else runner.EXIT_OWNER


def cmd_stop(args: argparse.Namespace) -> int:
    root = _root()
    pid = _active_run(root)
    if not pid:
        print("devpipe: no run is active in this project")
        return 0
    os.kill(pid, signal.SIGTERM)
    for _ in range(100):
        if not _active_run(root):
            print("devpipe: stopped; the ticket in progress was put back and not counted")
            return 0
        time.sleep(0.2)
    print(f"devpipe: asked pid {pid} to stop; it is still finishing a step")
    return 1


def cmd_pause(args: argparse.Namespace) -> int:
    """Ask the active run to stop once the ticket in progress ends; optionally wait for that."""
    root = _root()
    if not _active_run(root):
        print("devpipe: no run is active in this project")
        return 0
    pid_file, _log = _run_files(root)
    (pid_file.parent / runner.PAUSE_FILE).write_text("pause\n", encoding="utf-8")
    deadline = time.time() + max(args.wait, 0)
    while _active_run(root) and time.time() < deadline:
        time.sleep(0.5)
    if not _active_run(root):
        print("devpipe: paused; the run stopped between tickets. `devpipe status` shows where; "
              "`devpipe run --phase N --detach` continues")
        return 0
    print("devpipe: the run stops when the ticket in progress ends; it is still working. "
          "`devpipe pause --wait SECONDS` waits for it")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    root = _root()
    for ticket in tk.load_all(root):
        blockers = f" (after {', '.join(ticket.blocked_by)})" if ticket.blocked_by else ""
        print(f"{ticket.id}  {ticket.status:8} {ticket.mode:4} {ticket.title}{blockers}")
    pid = _active_run(root)
    print(f"runner: running (pid {pid})" if pid else "runner: not running")
    jobs = int((cfg.load(root).get("parallel") or {}).get("jobs") or 1)
    print(f"parallel: {jobs} tickets at a time without `--jobs` (parallel.jobs in .devpipe/config.json)" if jobs > 1
          else "parallel: 1 ticket at a time (parallel.jobs in .devpipe/config.json; `run --jobs K` overrides it)")
    noted = features.summary(root)
    if noted:
        print(f"features: {noted}")
    phase = _branch_phase(root)
    if phase and gates.commands(cfg.load(root)):
        owed = [row["command"] for row in gates.standing(root, cfg.load(root), phase) if not row["green_at"]]
        print(f"gate: phase {phase}: " + (f"{len(owed)} command(s) not green on this tree; `devpipe gate --check` lists them"
                                          if owed else "every gate command is green on this tree"))
    state = root / tk.TICKET_DIR / runner.STATE_FILE
    if state.is_file():
        print("last run state: " + json.dumps(json.loads(state.read_text(encoding="utf-8"))))
    _pid_file, log_file = _run_files(root)
    if log_file.is_file():
        print("last lines of the run log:")
        for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]:
            print("  " + line)
    return 0


def cmd_reads(args: argparse.Namespace) -> int:
    """Size of every unfinished ticket's read manifest as the files are now; exit 1 when one is over."""
    root = _root()
    config = cfg.load(root)
    counter = tokens.Counter(config.get("tokens") or {})
    rows = lint.read_report(root, config, args.phase, counter)
    if not rows:
        print("devpipe: no unfinished ticket" + (f" in phase {args.phase}" if args.phase else ""))
        return 0
    width = max(len(row["id"]) for row in rows)
    print(f"{'ticket':{width}}  status   tokens  of limit        largest entry")
    for row in rows:
        mark = {"over": "OVER", "near": "near", "ok": ""}[row["state"]]
        print(f"{row['id']:{width}}  {row['status']:7} {row['tokens']:7} {round(row['share'] * 100):8}%  {mark:4}  {row['largest']}")
        for note in row["watch"]:
            print(f"{'':{width}}    - {note}")
    limit = int(config["limits"]["read_tokens"])
    over = sum(1 for row in rows if row["state"] == "over")
    near = sum(1 for row in rows if row["state"] == "near")
    print(f"limit {limit} tokens (limits.read_tokens): {over} over, {near} at {round(lint.NEAR_SHARE * 100)}% or more, "
          f"of {len(rows)} unfinished")
    if not counter.exact:
        print(f"sizes are estimates ({counter.reason}); with the model server up they are exact")
    if over:
        print("a ticket over the limit blocks when it starts: narrow its `read:` entries to line ranges or sections")
    return 1 if over else 0


def cmd_limits(args: argparse.Namespace) -> int:
    """The limits in force for this project and where each comes from. Stages read them here."""
    root = _root()
    config = cfg.load(root)
    sources = cfg.limit_sources(root)
    print(f"profile: {config['profile']}"
          + (" (tickets may be executed on either tier)" if config["profile"] == "constrained"
             else " (tickets are sized for Claude Code; the local model cannot execute them)"))
    width = max(len(key) for key in config["limits"])
    for key, value in config["limits"].items():
        print(f"  {key:{width}}  {value!s:>7}  {sources.get(key, 'set in .devpipe/config.json')}")
    return 0


def cmd_triage(args: argparse.Namespace) -> int:
    """Every blocked ticket with its cause, its cost and what waits on it; exit 1 when there is one."""
    root = _root()
    rows = report.triage(root, args.phase)
    if not rows:
        print("devpipe: no blocked ticket" + (f" in phase {args.phase}" if args.phase else ""))
        return 0
    for row in rows:
        print(f"{row['id']}  {row['title']}")
        print(f"  reason:  {row['reason'] or 'not recorded'}")
        print(f"  detail:  {row['detail'][:600] or 'none'}")
        print(f"  spent:   {row['rounds']} engineer round(s)" + (f", {row['tokens']} input tokens" if row["tokens"] else ""))
        print(f"  waiting: {', '.join(row['waiting']) or 'nothing'}")
        print(f"  packet:  {row['packet']}")
    phases = sorted({row["phase"] for row in rows})
    waiting = {ticket for row in rows for ticket in row["waiting"]}
    print(f"{len(rows)} blocked ticket{'s' if len(rows) != 1 else ''} in phase{'s' if len(phases) != 1 else ''} "
          f"{', '.join(str(number) for number in phases)}; {len(waiting)} ticket{'s' if len(waiting) != 1 else ''} wait on them")
    return 1


def cmd_count(args: argparse.Namespace) -> int:
    root = cfg.find_root()
    settings = cfg.load(root)["tokens"] if root else dict(cfg.DEFAULTS["tokens"])
    if args.model:
        settings["model"] = args.model
    counter = tokens.Counter(settings)
    total = 0
    for name in args.files:
        size, exact = counter.count(Path(name).read_text(encoding="utf-8", errors="replace"))
        total += size
        print(f"{size:8d} {'exact' if exact else 'estimate'}  {name}")
    print(f"{total:8d} total" + ("" if counter.exact else f"  (estimates: {counter.reason})"))
    if args.max and total > args.max:
        print(f"over the limit of {args.max}")
        return 1
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """Print installed tool versions as rows for design/STACK.md."""
    print("| Name | Version | Role | Source |")
    print("|---|---|---|---|")
    for tool in PROBE_TOOLS:
        path = shutil.which(tool)
        if not path:
            continue
        try:
            done = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = (done.stdout or done.stderr).strip().splitlines()
        first = output[0].strip() if output else ""
        print(f"| {tool} | {first} | <<role>> | `{tool} --version` on {cfg.host_kind()} |")
    return 0


def cmd_ticket(args: argparse.Namespace) -> int:
    root = _root()
    matches = [ticket for ticket in tk.load_all(root) if ticket.id == args.id]
    if not matches:
        sys.exit(f"devpipe: no ticket {args.id}")
    ticket = matches[0]
    if args.status == "todo" and not git.is_clean(root):
        # `todo` retries a ticket as it stands. Seen in a pilot: run after a triage's edits, it committed
        # every edited ticket and a plan change as "[P02.T08] reopened", and the triage commit found nothing left.
        changed = git.changed_files(root)
        print(f"devpipe: `ticket todo` commits {ticket.id}'s status line and nothing else, and the tree has other changes:")
        for path in changed[:10]:
            print(f"  {path}")
        if len(changed) > 10:
            print(f"  and {len(changed) - 10} more")
        print("devpipe: commit them first under their own message (`devpipe checkpoint tickets-PNN \"triage: …\"`); "
              "an amended ticket can carry `status: todo` in that same edit")
        return runner.EXIT_OWNER
    # `done`: whatever the owner changed by hand is committed together with the status line.
    tk.set_status(ticket, args.status)
    if args.status == "done":
        report.ledger(root, ticket, "done by the owner", {})
        for closed in features.close_finished(root):
            print(f"{closed} is now DONE")
    git.commit_all(root, f"{report.tag(ticket)} {'done by the owner' if args.status == 'done' else 'reopened'}: {ticket.title}")
    print(f"{ticket.id} is now {args.status}")
    if args.status != "done" or any(other.status != "done" for other in tk.load_phase(root, ticket.phase)):
        return 0
    # The last ticket of the phase: the phase is complete only when its gate has run and its
    # review brief is written, and no other command gets here when the last ticket is closed by hand.
    branch = f"phase/{ticket.phase:02d}"
    print(f"devpipe: every ticket of phase {ticket.phase} is done")
    if _active_run(root):
        print("devpipe: a run is active and will complete the phase")
        return 0
    if git.branch(root) != branch:
        print(f"devpipe: the phase is not complete yet: run `devpipe run --phase {ticket.phase}` to run the phase gate "
              f"and write the review brief (this is not branch `{branch}`)")
        return 0
    try:
        return runner.Runner(root, ticket.phase)._finish_phase()
    except (git.GitError, cfg.ConfigError, tk.TicketError) as error:
        print(f"devpipe: the phase gate and the review brief are still to do (`devpipe run --phase {ticket.phase}`): {error}")
        return runner.EXIT_INFRA


def _branch_phase(root: Path, name: str = "") -> int:
    """The phase a branch name stands for (`phase/07`, also behind a remote's name), or 0. The current branch by default."""
    if not name and not (git.is_repo(root) and git.has_commits(root)):
        return 0
    found = re.search(r"(?:^|/)phase/(\d{2,3})$", name or git.branch(root))
    return int(found.group(1)) if found else 0


def _print_standing(rows: List[dict]) -> int:
    """Print where each gate command stands; return how many are owed."""
    for row in rows:
        kind = "long suite" if row["kind"] == gates.SEAM else "quick"
        if row["green_at"]:
            print(f"green  {kind:10}  `{row['command']}`  passed on {row['green_at'][:8]}")
            continue
        print(f"owed   {kind:10}  `{row['command']}`  {row['why']}")
        changed = row["changed"]
        for path in changed[:10]:
            print(f"         {path}")
        if len(changed) > 10:
            print(f"         and {len(changed) - 10} more")
    return sum(1 for row in rows if not row["green_at"])


def cmd_gate(args: argparse.Namespace) -> int:
    """The gate before the merge: run what the tree to be merged has not passed, or with --check only say what that is."""
    root = _root()
    config = cfg.load(root)
    if args.merging:
        # Asked by the merge hooks. Exit 1 refuses the merge; anything this command cannot judge lets it through.
        commit = git.git(root, "rev-parse", "--verify", "-q", f"{args.merging}^{{commit}}", check=False)
        if not commit or _branch_phase(root):
            return 0                                 # not a commit, or the merge goes into a phase branch
        named = _branch_phase(root, args.merging)
        phases = [named] if named else sorted({_branch_phase(root, ref) for ref in git.git(
            root, "for-each-ref", "--points-at", commit, "--format=%(refname:short)", "refs/heads/phase/", check=False).split()} - {0})
        refused = 0
        for phase in phases:
            owed = [row for row in gates.standing(root, config, phase, at=commit) if not row["green_at"]]
            if owed:
                refused = 1
                print(f"devpipe: phase/{phase:02d} is not green for a merge; {len(owed)} gate command(s) have not passed on its tree:")
                _print_standing(owed)
                print(f"devpipe: on branch phase/{phase:02d}, run `devpipe gate --phase {phase}` "
                      f"(`python3 tools/devpipe/run.py gate --phase {phase}`), then merge again")
        return refused
    phase = args.phase or _branch_phase(root)
    if not phase:
        sys.exit("devpipe: name the phase: devpipe gate --phase N (this branch is not a phase branch)")
    if args.check:
        rows = gates.standing(root, config, phase)
        if not rows:
            print("devpipe: no gate command is configured in .devpipe/config.json (phase_gate, seam_gate)")
            return 0
        owed = _print_standing(rows)
        print(f"devpipe: phase {phase}: " + (f"{owed} gate command(s) owed on this tree; `devpipe gate --phase {phase}` runs them"
                                             if owed else "every gate command is green on this tree"))
        return 1 if owed else 0
    branch = f"phase/{phase:02d}"
    if _active_run(root):
        print("devpipe: a run is active in this project; the gate before the merge waits until it has stopped")
        return runner.EXIT_OWNER
    if git.branch(root) != branch:
        print(f"devpipe: the gate before the merge tests the tree that is merged: `git switch {branch}` first "
              f"(this is `{git.branch(root)}`)")
        return runner.EXIT_OWNER
    if not git.is_clean(root):
        print("devpipe: the working tree has uncommitted changes; commit or discard them first, so the result "
              "belongs to a commit")
        return runner.EXIT_OWNER
    code = runner.Runner(root, phase).merge_gate()
    _print_standing(gates.standing(root, config, phase))
    return code


# What a commit tagged `tickets-PNN` is expected to hold: tickets, their review, and the plan and design they amend.
TICKETS_COMMIT_PATHS = (".tickets/", "docs/qa/reviews/", "design/", "DEV_PLAN.md")


def _print_committed(root: Path, tag: str) -> None:
    """Name every file the commit just made holds, and for a tickets commit whatever else rode along.

    Seen in a pilot: a `checkpoint tickets-P02` also committed an unrelated configuration change,
    which a phase review reads past under a tickets message.
    """
    files = [path for path in git.git(root, "show", "--name-only", "--format=", "HEAD").splitlines() if path]
    for path in files[:40]:
        print(f"  {path}")
    if len(files) > 40:
        print(f"  and {len(files) - 40} more")
    if tag.startswith("tickets-"):
        other = [path for path in files if not path.startswith(TICKETS_COMMIT_PATHS)]
        if other:
            print(f"NOTE this [{tag}] commit also holds {', '.join(other[:8])}{' …' if len(other) > 8 else ''}: say so to "
                  "the owner, or give such a change its own commit next time (`checkpoint <tag> <message> --only <paths>`)")


def cmd_notes(args: argparse.Namespace) -> int:
    """What the loop saw and left for a person: Engineers' notes for the owner, and the per-ticket Reviewer's findings."""
    root = _root()
    phase = args.phase or _branch_phase(root)
    tickets = [ticket for ticket in tk.load_all(root) if not phase or ticket.phase == phase]
    notes, findings = report.owner_notes(root, tickets), report.loop_findings(root, tickets)
    scope = f"phase {phase}" if phase else "every phase"
    print(f"Engineer notes for the owner ({scope}): {len(notes)}")
    for ticket_id, note in notes:
        print(f"  {ticket_id}  {note}")
    print(f"Findings the per-ticket Reviewer recorded ({scope}): {len(findings)}")
    for row in findings:
        print(f"  {row['id']}  {row['severity']}  {row['place'].strip('`')}  {row['claim']}")
    if not notes and not findings:
        print("devpipe: nothing recorded (the notes and findings live in .tickets/.work/, which is kept on this machine only)")
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    """Commit everything with a tagged message; how a stage records its output."""
    root = _root()
    if args.only:
        # Only these paths: whatever else is uncommitted is somebody's work in progress.
        if not git.git(root, "status", "--porcelain", "--", *args.only):
            print("nothing to commit")
            return 0
        commit = git.commit_paths(root, args.only, f"[{args.tag}] {args.message}")
        print(f"committed {commit[:8]} [{args.tag}] {args.message}")
        _print_committed(root, args.tag)
        return 0
    if git.is_clean(root) and git.has_commits(root):
        print("nothing to commit")
        return 0
    commit = git.commit_all(root, f"[{args.tag}] {args.message}")
    print(f"committed {commit[:8]} [{args.tag}] {args.message}")
    _print_committed(root, args.tag)
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    """Mockup housekeeping for the ui-design stage: templates, gallery, pictures, viewing."""
    root = _root()
    try:
        if args.action == "init":
            written = ui.init(root)
            for path in written:
                print(f"written: {path}")
            print("screen template: tools/devpipe/templates/ui/screen.html "
                  "(copy it to design/ui/S-01-<name>.html for each screen)")
            if not written:
                print("design/UI.md and design/ui/tokens.css already exist; nothing written")
        elif args.action == "index":
            page = ui.index(root)
            print(f"written: {page.relative_to(root)} ({len(ui.mockups(root))} mockup file(s))")
        elif args.action == "render":
            for picture in ui.render(root, args.screens, args.scale):
                print(f"rendered: {picture.relative_to(root)}")
        elif args.action == "open":
            print(f"opened: {ui.open_gallery(root).relative_to(root)}")
        elif args.action == "parts":
            if len(args.screens) != 1:
                sys.exit("devpipe: name one screen: devpipe ui parts S-01")
            counter = tokens.Counter(cfg.load(root).get("tokens") or {})
            for line in ui.parts(root, args.screens[0], counter):
                print(line)
        elif args.action == "compare":
            if not (root / ui.UI_FILE).is_file():
                # Seen in a pilot: a project with native screens and no mockups was told a `Built:` line was missing.
                print(f"devpipe: this project has no {ui.UI_FILE}, so there is no mockup to compare a screen with; "
                      "screens built without mockups are checked by hand")
                return 0
            wanted = args.screens or ui.with_built(root)
            if args.built and len(wanted) != 1:
                sys.exit("devpipe: --built goes with exactly one screen: devpipe ui compare S-01 --built <where>")
            if not wanted:
                print("devpipe: no screen in design/UI.md has a 'Built:' line yet; name a screen and pass --built <where>")
                return 1
            for screen_id in wanted:
                page, picture = ui.compare(root, screen_id, args.built or "")
                print(f"compared {screen_id}: {picture.relative_to(root)} (page: {page.relative_to(root)})")
                if args.open:
                    subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(page)], check=False,
                                   stdin=subprocess.DEVNULL)
        else:
            ui.serve(root, args.host, args.port)
    except ui.UiError as error:
        print(f"devpipe: {error}")
        return 1
    return 0


def _file_inbox(root: Path) -> None:
    """Turn ideas captured during a run into records, one commit each."""
    for feature in features.file_inbox(root):
        relative = str(feature.path.relative_to(root))
        git.commit_paths(root, [relative], f"[{feature.id}] proposed: {feature.title}")
        print(f"{feature.id} filed from the inbox: {relative}")


def _csv(text: str) -> List[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def cmd_feature(args: argparse.Namespace) -> int:
    root = _root()
    active = _active_run(root)
    branch = features.work_branch(root)
    elsewhere = bool(branch) and git.branch(root) != branch
    if args.action == "new":
        idea = " ".join(args.words).strip()
        if not idea:
            sys.exit("devpipe: give the idea in words: devpipe feature new \"<idea>\"")
        if active:
            # The runner discards or resets files that appear while a ticket is in progress,
            # so the idea waits outside the tracked tree until the run is idle.
            waiting = features.inbox_add(root, idea, args.title or "")
            print(f"captured in the inbox ({waiting} waiting): a run is active, so the idea gets its "
                  "F-number when `devpipe feature list` runs with no run active")
            return 0
        if elsewhere:
            print(f"devpipe: the phase in progress is on branch `{branch}` and this is `{git.branch(root)}`; "
                  f"`git switch {branch}`, then run this again")
            return runner.EXIT_OWNER
        _file_inbox(root)
        feature = features.new(root, idea, args.title or "")
        relative = str(feature.path.relative_to(root))
        git.commit_paths(root, [relative], f"[{feature.id}] proposed: {feature.title}")
        print(f"{feature.id} created: {relative}")
        return 0
    if args.action == "list":
        if not active and not elsewhere:
            _file_inbox(root)
        for line in features.listing(root):
            print(line)
        return 0
    feature = None
    if args.words:
        matches = [found for found in features.load_all(root) if found.id == args.words[0]]
        if not matches:
            sys.exit(f"devpipe: no feature {args.words[0]}")
        feature = matches[0]
    run_note = "not running"
    if active:
        state = root / tk.TICKET_DIR / runner.STATE_FILE
        ticket = json.loads(state.read_text(encoding="utf-8")).get("ticket", "?") if state.is_file() else "?"
        run_note = f"active (pid {active}), working on {ticket}; `devpipe pause --wait SECONDS` stops it between tickets"
    print(features.impact(root, _csv(args.touches) or (feature.touches if feature else []),
                          _csv(args.changes) or (feature.changes if feature else []), feature, run_note))
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    root = _root()
    config = cfg.load(root)
    tiers = [args.tier] if args.tier != "both" else ["opencode", "claude"]
    written = scaffold.init_agents(root, config, tiers)
    for path in written:
        print(f"written: {path}")
    if not written:
        print("agent files already exist; nothing written")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devpipe", description="Toolkit behind the idea-to-implementation pipeline.")
    parser.add_argument("--version", action="version", version=f"devpipe {VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)

    for name, text in (("doctor", "set up this folder as a pipeline project, or repair it"),
                       ("sync", "like doctor, and refresh the vendored toolkit copy")):
        sub = commands.add_parser(name, help=text)
        sub.add_argument("--check", action="store_true", help="report what is missing; change nothing")
        sub.add_argument("--adapter", choices=["opencode", "claude"], help="execution adapter for a new project")
        sub.add_argument("--slug", help="short project name used in agent names")
        if name == "sync":
            sub.add_argument("--discard-local", action="store_true",
                             help="refresh the vendored toolkit even though the project has changed its copy")
        sub.set_defaults(handler=cmd_doctor)

    sub = commands.add_parser("lint", help="check artifacts; exit 1 on any error")
    sub.add_argument("what", choices=["spec", "plan", "tickets", "agents", "features", "ui", "all"])
    sub.add_argument("--phase", type=int, help="tickets: only this phase, and check plan coverage for it")
    sub.add_argument("--allow-open", action="store_true",
                     help="spec, ui: open items and screens not yet accepted are warnings while the design is in progress")
    sub.set_defaults(handler=cmd_lint)

    sub = commands.add_parser("run", help="run one phase's tickets; commits locally, never pushes")
    sub.add_argument("--phase", type=int, required=True)
    sub.add_argument("--continue-on-block", action="store_true", help="keep going with other ready tickets after a block")
    sub.add_argument("--max-tickets", type=int, default=0, help="stop after this many tickets (0 = no limit)")
    sub.add_argument("--detach", action="store_true", help="run in the background; output goes to .tickets/.work/run.log")
    sub.add_argument("--jobs", type=int, default=0,
                     help="work up to this many tickets at a time, each in its own git worktree "
                          "(default: parallel.jobs in the config, which is 1; claude adapter only)")
    sub.set_defaults(handler=cmd_run)

    sub = commands.add_parser("worker", help="internal: one ticket's attempt in a worktree, started by `run --jobs`")
    sub.add_argument("--phase", type=int, required=True)
    sub.add_argument("--ticket", required=True)
    sub.set_defaults(handler=cmd_worker)

    sub = commands.add_parser("stop", help="end the active run cleanly; the ticket in progress is put back")
    sub.set_defaults(handler=cmd_stop)

    sub = commands.add_parser("pause", help="stop the active run once the ticket in progress ends")
    sub.add_argument("--wait", type=int, default=0, help="wait up to this many seconds; exit 1 if it is still working")
    sub.set_defaults(handler=cmd_pause)

    sub = commands.add_parser("status", help="list tickets, whether a run is active, and the end of its log")
    sub.set_defaults(handler=cmd_status)

    sub = commands.add_parser("reads", help="size of every unfinished ticket's read manifest now; exit 1 when one is over its limit")
    sub.add_argument("--phase", type=int, help="only this phase")
    sub.set_defaults(handler=cmd_reads)

    sub = commands.add_parser("limits", help="the profile and the limits in force, and where each comes from")
    sub.set_defaults(handler=cmd_limits)

    sub = commands.add_parser("triage", help="every blocked ticket with its cause, cost and what waits on it; exit 1 when there is one")
    sub.add_argument("--phase", type=int, help="only this phase")
    sub.set_defaults(handler=cmd_triage)

    sub = commands.add_parser("gate", help="the gate before the merge: run every gate command this tree has not passed; "
                                           "exit 0 only when all are green")
    sub.add_argument("--phase", type=int, help="the phase (default: the one this branch is named for)")
    sub.add_argument("--check", action="store_true", help="say what this tree owes and run nothing; exit 1 when something is owed")
    sub.add_argument("--merging", metavar="NAME", help=argparse.SUPPRESS)      # the merge hooks: is NAME green for a merge?
    sub.set_defaults(handler=cmd_gate)

    sub = commands.add_parser("notes", help="what Engineers wrote for the owner and what the per-ticket Reviewer recorded")
    sub.add_argument("--phase", type=int, help="only this phase (default: the one this branch is named for, else all)")
    sub.set_defaults(handler=cmd_notes)

    sub = commands.add_parser("count", help="count tokens in files with the serving model's tokenizer")
    sub.add_argument("files", nargs="+")
    sub.add_argument("--max", type=int, default=0, help="exit 1 when the total exceeds this")
    sub.add_argument("--model", help="model name the server reports (outside a project)")
    sub.set_defaults(handler=cmd_count)

    sub = commands.add_parser("probe", help="print installed tool versions as STACK.md rows")
    sub.set_defaults(handler=cmd_probe)

    sub = commands.add_parser("ticket", help="set a ticket's status by hand and commit that")
    sub.add_argument("status", choices=["done", "todo"])
    sub.add_argument("id")
    sub.set_defaults(handler=cmd_ticket)

    sub = commands.add_parser("checkpoint", help="commit all changes as '[tag] message'")
    sub.add_argument("tag", help="for example design, plan, tickets-P02, agents, P00")
    sub.add_argument("message")
    sub.add_argument("--only", nargs="+", metavar="PATH", help="commit just these paths and leave other changes alone")
    sub.set_defaults(handler=cmd_checkpoint)

    sub = commands.add_parser("ui", help="UI mockups: templates, gallery page, pictures, viewing")
    sub.add_argument("action", choices=["init", "index", "render", "open", "serve", "parts", "compare"],
                     help="init: copy design/UI.md and tokens.css templates; index: write design/ui/index.html; "
                          "render: mockups to PNG in design/ui/renders/; open: gallery in the default browser; "
                          "serve: design/ui/ over HTTP; parts: a mockup's line ranges and sizes for ticket read lists; "
                          "compare: the built screen beside its mockup, with their difference")
    sub.add_argument("screens", nargs="*", help="render, compare: screen ids such as S-01 (default: all); parts: one id")
    sub.add_argument("--built", help="compare: where the built screen is, instead of the screen's 'Built:' line: "
                                     "an http address, a file, or 'run <command>' that prints its HTML")
    sub.add_argument("--open", action="store_true", help="compare: open the comparison page in the browser")
    sub.add_argument("--scale", type=int, default=2, help="render: pixels per CSS pixel (default 2)")
    sub.add_argument("--host", default="127.0.0.1", help="serve: address to listen on (default this machine only)")
    sub.add_argument("--port", type=int, default=8765, help="serve: port (default 8765)")
    sub.set_defaults(handler=cmd_ui)

    sub = commands.add_parser("feature", help="capture, list or assess a feature that turned up mid-development")
    sub.add_argument("action", choices=["new", "list", "impact"])
    sub.add_argument("words", nargs="*", help="new: the idea in words; impact: a feature id such as F-003")
    sub.add_argument("--title", help="new: a short title (default: the idea's first words)")
    sub.add_argument("--touches", default="", help="impact: comma-separated files the feature creates or modifies")
    sub.add_argument("--changes", default="", help="impact: comma-separated requirements whose text it changes")
    sub.set_defaults(handler=cmd_feature)

    sub = commands.add_parser("agents", help="copy the agent skeletons into the project")
    sub.add_argument("tier", choices=["opencode", "claude", "both"])
    sub.set_defaults(handler=cmd_agents)
    return parser


TRAILING_OPTIONS = {"feature": ("--title", "--touches", "--changes"), "ui": ("--scale", "--host", "--port", "--built")}


def _options_last(argv: List[str]) -> List[str]:
    """Move the options of `feature` and `ui` behind their words.

    Before Python 3.12 argparse gives a `nargs="*"` positional nothing when an
    option stands in front of it, so `feature new --title T "idea"` would fail.
    """
    if len(argv) >= 5 and argv[0] == "checkpoint" and argv[1] == "--only":
        # `--only` takes every word after it, the tag and the message included. Written first,
        # the last two words are those two: `checkpoint --only a b tag "message"`.
        return ["checkpoint", argv[-2], argv[-1], "--only", *argv[2:-2]]
    if not argv or argv[0] not in TRAILING_OPTIONS:
        return argv
    named = TRAILING_OPTIONS[argv[0]]
    words, options, index = [], [], 0
    while index < len(argv):
        item = argv[index]
        if item in named and index + 1 < len(argv):
            options += argv[index:index + 2]
            index += 2
        elif item.startswith(tuple(option + "=" for option in named)):
            options.append(item)
            index += 1
        else:
            words.append(item)
            index += 1
    return words + options


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(_options_last(list(sys.argv[1:] if argv is None else argv)))
    try:
        return int(args.handler(args))
    except (cfg.ConfigError, git.GitError, tk.TicketError, features.FeatureError) as error:
        print(f"devpipe: {error}")
        return runner.EXIT_INFRA
