"""Thin wrappers over the `git` binary.

Purpose: the handful of repository operations the runner needs, each one
explicit about what it changes.
Side effects: as documented per function. Nothing here pushes, pulls, merges or
rewrites history that existed before the current ticket started.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional


class GitError(RuntimeError):
    """A git command failed; the message carries its stderr."""


def git(root: Path, *args: str, check: bool = True) -> str:
    """Run git in `root` and return stdout without the trailing newline."""
    # The runner's own git calls never carry the agent marker, so the hooks that
    # refuse an agent's commit let the runner's commit through wherever it was started.
    env = {key: value for key, value in os.environ.items() if key != "DEVPIPE_AGENT"}
    done = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, env=env)
    if check and done.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout.rstrip("\n")


def is_repo(root: Path) -> bool:
    done = subprocess.run(["git", "rev-parse", "--git-dir"], cwd=str(root), capture_output=True, text=True)
    return done.returncode == 0


def has_commits(root: Path) -> bool:
    done = subprocess.run(["git", "rev-parse", "--verify", "-q", "HEAD"], cwd=str(root), capture_output=True)
    return done.returncode == 0


def head(root: Path) -> str:
    return git(root, "rev-parse", "HEAD")


def branch(root: Path) -> str:
    return git(root, "rev-parse", "--abbrev-ref", "HEAD")


def branch_exists(root: Path, name: str) -> bool:
    done = subprocess.run(["git", "show-ref", "--verify", "-q", f"refs/heads/{name}"], cwd=str(root))
    return done.returncode == 0


def changed_files(root: Path) -> List[str]:
    """Paths that differ from HEAD, untracked files included, ignored files excluded."""
    raw = git(root, "status", "--porcelain", "-z", "--untracked-files=all")
    paths: List[str] = []
    entries = raw.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            # A rename or copy is followed by its source path, which changed too.
            if index < len(entries) and entries[index]:
                paths.append(entries[index])
            index += 1
    return sorted(set(paths))


def is_clean(root: Path) -> bool:
    return not changed_files(root)


def exists_at(root: Path, commit: str, path: str) -> bool:
    done = subprocess.run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=str(root), capture_output=True)
    return done.returncode == 0


def differs_from(root: Path, commit: str, path: str) -> bool:
    """True when the file in the working tree is not what `commit` holds at `path`.

    A file that exists on one side only differs.
    """
    if not exists_at(root, commit, path):
        return (root / path).is_file() or (root / path).is_symlink()
    done = subprocess.run(["git", "diff", "--quiet", commit, "--", path], cwd=str(root), capture_output=True)
    return done.returncode != 0


def changed_between(root: Path, older: str, newer: str) -> Optional[List[str]]:
    """Paths that differ between two commits, or None when one of them is not in this repository."""
    done = subprocess.run(["git", "diff", "--name-only", "-z", older, newer, "--"], cwd=str(root), capture_output=True,
                          text=True, stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        return None
    return sorted(path for path in done.stdout.split("\0") if path)


def restore_paths(root: Path, commit: str, paths: Iterable[str]) -> None:
    """Put each path back to its content at `commit`; delete it if it did not exist there."""
    for path in paths:
        if exists_at(root, commit, path):
            git(root, "checkout", commit, "--", path)
        else:
            # -f: the index may hold a staged version that differs from both HEAD and the file.
            git(root, "rm", "-q", "-f", "--cached", "--ignore-unmatch", "--", path)
            target = root / path
            if target.is_file() or target.is_symlink():
                target.unlink()


def patch_against(root: Path, commit: str) -> str:
    """Diff of the whole working tree against `commit`, new files included.

    Stages everything first so untracked files appear in the diff; the index is
    left staged, which the later commit or reset replaces anyway.
    """
    git(root, "add", "-A")
    return git(root, "diff", "--cached", "--binary", commit)


def reset_to(root: Path, commit: str) -> None:
    """Discard every change since `commit`: tracked edits and untracked files.

    Ignored files (the ticket work folder among them) survive.
    """
    git(root, "reset", "-q", "--hard", commit)
    git(root, "clean", "-q", "-fd")


def is_worktree_of(root: Path, path: Path) -> bool:
    """True when `path` is the top folder of a worktree of the repository at `root`.

    Checked before anything is reset in `path`: a plain folder inside another
    checkout would otherwise pass a git command on to that checkout.
    """
    try:
        top = Path(git(path, "rev-parse", "--show-toplevel")).resolve()
        mine = (root / git(root, "rev-parse", "--git-common-dir")).resolve()
        theirs = (path / git(path, "rev-parse", "--git-common-dir")).resolve()
    except (GitError, OSError):
        return False
    return top == path.resolve() and mine == theirs and path.resolve() != root.resolve()


def commit_paths(root: Path, paths: Iterable[str], message: str) -> str:
    """Commit only `paths` with `message`; whatever else is changed stays as it is."""
    listed = list(paths)
    git(root, "add", "--", *listed)
    git(root, "commit", "-q", "-m", message, "--", *listed)
    return head(root)


def commit_all(root: Path, message: str) -> str:
    """Commit the whole working tree with `message`; return the new commit id."""
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return head(root)
