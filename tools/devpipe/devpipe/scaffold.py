"""Project setup and drift repair (`devpipe doctor`, `devpipe sync`).

Purpose: make any folder a pipeline project with no manual copying, and keep
its vendored toolkit current. Every stage starts by calling `doctor`.
Dependencies: config, gitutil.
Side effects: creates folders and files inside the project, may run `git init`
and sets the repository-local `core.hooksPath`. Never touches global git or
tool configuration.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List

from . import VERSION, config as cfg, gitutil as git

VENDOR_DIR = "tools/devpipe"
HOOKS_DIR = ".githooks"
IGNORE_LINES = [".tickets/.run-state.json", ".tickets/.work/", "__pycache__/"]
FOLDERS = ["design", ".tickets", "docs/ledger", "docs/qa/reviews"]
SKELETON_TARGETS = {"opencode": ".opencode/agents", "claude": ".claude/agents"}
ROLES = ("engineer", "reviewer", "diagnostic")


def toolkit_dir() -> Path:
    """Folder that holds this toolkit: the package, templates, skeletons and hooks."""
    return Path(__file__).resolve().parent.parent


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"


def _opencode_model() -> str:
    """The default model from the local OpenCode config, or an empty string."""
    try:
        text = Path(os.path.expanduser("~/.config/opencode/opencode.json")).read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r'"model"\s*:\s*"([^"/]+/[^"]+)"', text)
    return match.group(1) if match else ""


def default_config(root: Path, adapter: str = "", slug: str = "") -> Dict[str, Any]:
    """A first config for a new project, derived from the machine it is created on."""
    slug = slugify(slug or root.name)
    model = _opencode_model()
    if not adapter:
        adapter = "opencode" if model else "claude"
    data: Dict[str, Any] = {
        "version": 1,
        "slug": slug,
        "adapter": adapter,
        # Tickets are sized for the tier that executes them; a project that should stay
        # executable on the local model keeps "constrained" (mixed mode needs it).
        "profile": "claude" if adapter == "claude" else "constrained",
        "model": model if adapter == "opencode" else "",
        "agents": {role: f"{slug}-{role}" for role in ROLES},
        "phase_gate": [],
        "scope_allow": [],
    }
    if model:
        data["tokens"] = {"model": model.split("/", 1)[1], "provider": model.split("/", 1)[0]}
    return data


def _copy_toolkit(target: Path) -> None:
    source = toolkit_dir()
    if target.exists():
        shutil.rmtree(target)
    # "._*" and .DS_Store are macOS metadata that an archive made on a Mac can carry along.
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests", "._*", ".DS_Store"))


def vendored_version(root: Path) -> str:
    path = root / VENDOR_DIR / "devpipe" / "__init__.py"
    try:
        match = re.search(r'^VERSION = "([^"]+)"', path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    except OSError:
        return ""
    return match.group(1) if match else ""


def vendored_local_changes(root: Path) -> List[str]:
    """What has changed in the project's vendored toolkit since it was vendored: one line per
    commit that touched it and per uncommitted file. Empty when there is nothing, or no way to tell.

    The base is the last commit that changed the toolkit's VERSION line, which is the commit that
    vendored or refreshed it. A project may patch its copy to close a fault at once; a refresh
    replaces the whole folder, so it must not happen while such a patch has not been seen upstream.
    """
    vendor = root / VENDOR_DIR
    if not vendor.is_dir() or not git.is_repo(root) or not git.has_commits(root):
        return []
    found: List[str] = []
    base = git.git(root, "log", "-1", "--format=%H", "-G", "^VERSION = ", "--", f"{VENDOR_DIR}/devpipe/__init__.py", check=False)
    if base:
        found += [f"commit {line}" for line in
                  git.git(root, "log", "--format=%h %s", f"{base}..HEAD", "--", VENDOR_DIR, check=False).splitlines()]
    found += [f"uncommitted: {line[3:]}" for line in
              git.git(root, "status", "--porcelain", "--", VENDOR_DIR, check=False).splitlines() if line.strip()]
    return found


def doctor(root: Path, fix: bool = True, adapter: str = "", slug: str = "", refresh: bool = False,
           busy: bool = False, discard_local: bool = False) -> List[str]:
    """Set up or repair a project. Returns one line per thing done (or, with fix=False, needed).

    `busy` says a run is active: the vendored toolkit and the hooks are then left alone, because
    they are the code that run is executing and the runner discards files that change under it.
    """
    notes: List[str] = []

    def act(description: str, action) -> None:
        notes.append(description)
        if fix:
            action()

    if not git.is_repo(root):
        act("git repository created (branch main)", lambda: git.git(root, "init", "-q", "-b", "main"))
    if not (root / cfg.CONFIG_DIR / cfg.CONFIG_FILE).is_file():
        act(f"{cfg.CONFIG_DIR}/{cfg.CONFIG_FILE} written", lambda: cfg.save(root, default_config(root, adapter, slug)))
    for folder in FOLDERS:
        if not (root / folder).is_dir():
            act(f"{folder}/ created", lambda folder=folder: (root / folder).mkdir(parents=True, exist_ok=True))
    ignore = root / ".gitignore"
    present = ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []
    missing = [line for line in IGNORE_LINES if line not in present]
    if missing:
        act(".gitignore: " + ", ".join(missing), lambda: ignore.write_text(
            "\n".join(present + missing) + "\n", encoding="utf-8"))
    vendor = root / VENDOR_DIR
    running_vendored = toolkit_dir() == vendor.resolve()
    stale = not running_vendored and (refresh or vendored_version(root) != VERSION)
    if stale and busy:
        notes.append(f"NOTE a run is active, so {VENDOR_DIR}/ (at {vendored_version(root) or 'no version'}) was not "
                     f"refreshed to {VERSION}; run this again when the run is idle")
    elif stale and not discard_local and vendored_local_changes(root):
        local = vendored_local_changes(root)
        shown = "; ".join(local[:6]) + (f"; and {len(local) - 6} more" if len(local) > 6 else "")
        notes.append(f"NOTE {VENDOR_DIR}/ (at {vendored_version(root) or 'no version'}) has local changes and was not "
                     f"refreshed to {VERSION}, which would discard them: {shown}. Check that each is in devpipe "
                     f"{VERSION} (or no longer wanted), then run `devpipe sync --discard-local`")
    elif stale:
        was = vendored_version(root) or "absent"
        act(f"{VENDOR_DIR}/ vendored at {VERSION} (was {was})", lambda: _copy_toolkit(vendor))
    elif running_vendored and refresh:
        # A copy cannot refresh itself; saying nothing would look like a refresh that found no change.
        notes.append(f"NOTE {VENDOR_DIR}/ is the copy now running and was not refreshed; "
                     "run the installed one instead: `devpipe sync`")
    hooks = root / HOOKS_DIR
    source_hooks = toolkit_dir() / "hooks"
    for hook in sorted(source_hooks.glob("*")) if source_hooks.is_dir() and not busy else []:
        if hook.name.startswith("."):
            continue
        target = hooks / hook.name
        if target.is_file() and b"# devpipe-managed" not in target.read_bytes():
            # A hook the project wrote itself is never replaced.
            notes.append(f"NOTE {HOOKS_DIR}/{hook.name} is the project's own; merge tools/devpipe/hooks/{hook.name} into it by hand")
            continue
        if not target.is_file() or target.read_bytes() != hook.read_bytes():
            def install(hook=hook, target=target) -> None:
                hooks.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(hook, target)
                target.chmod(0o755)
            act(f"{HOOKS_DIR}/{hook.name} installed", install)
    if git.is_repo(root) or fix:
        current = git.git(root, "config", "--local", "--get", "core.hooksPath", check=False) if git.is_repo(root) else ""
        if not current:
            act(f"git core.hooksPath set to {HOOKS_DIR} (this repository only)",
                lambda: git.git(root, "config", "--local", "core.hooksPath", HOOKS_DIR))
        elif current != HOOKS_DIR:
            notes.append(f"NOTE core.hooksPath is {current!r}; copy {HOOKS_DIR}/* there to keep the commit rules")
    return notes


def init_agents(root: Path, config: Dict[str, Any], tiers: List[str]) -> List[str]:
    """Copy the agent skeletons into the project with the slug filled in.

    Existing agent files are left alone. The copies still hold <<…>> blanks for
    the architect stage; `devpipe lint agents` fails until they are filled.
    """
    written: List[str] = []
    for tier in tiers:
        folder = root / SKELETON_TARGETS[tier]
        folder.mkdir(parents=True, exist_ok=True)
        for role in ROLES:
            name = str(config["agents"][role])
            target = folder / f"{name}.md"
            if target.exists():
                continue
            text = (toolkit_dir() / "skeletons" / tier / f"{role}.md").read_text(encoding="utf-8")
            target.write_text(text.replace("{{name}}", name).replace("{{slug}}", str(config["slug"])), encoding="utf-8")
            written.append(str(target.relative_to(root)))
    return written
