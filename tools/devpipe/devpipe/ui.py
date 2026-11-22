"""UI design records (`design/UI.md`, `design/ui/`).

Purpose: make the interface a designed, checked part of the plan instead of
something the first engineer improvises. `design/UI.md` lists numbered screens
with what each shows, does and serves; `design/ui/` holds one HTML mockup per
screen plus the design tokens they share. This module creates those files from
templates, builds a gallery page, turns mockups into pictures the owner (and a
model that can see) can judge, and checks that the record is complete and that
the development plan builds every screen.
Dependencies: lint (issues, section parsing, stack and requirement ids); for
rendering, a Chrome-family browser or Firefox, or on macOS the Swift toolchain.
Side effects: `init`, `index` and `render` write under `design/`; `serve`
listens on a local port until stopped; `open_gallery` starts the default
browser. Nothing here commits.
"""
from __future__ import annotations

import functools
import html
import http.server
import os
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import lint

UI_FILE = "design/UI.md"
UI_DIR = "design/ui"
RENDER_DIR = "design/ui/renders"
# Pictures of the built product change with every build, so they live in the ignored work folder.
COMPARE_DIR = ".tickets/.work/ui-compare"
SECTIONS = ["Surfaces", "Users and tasks", "Screens", "Flows", "Navigation", "Visual language",
            "Components", "Accessibility", "Tooling", "Not yet decided"]
SCREEN_FIELDS = ["Purpose", "Serves", "Shows", "Actions", "States", "Mockup", "Status"]
DEFAULT_VIEWPORT = (1280, 800)
RENDER_TIMEOUT_S = 90
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"]
MAC_CHROME_APPS = ["Google Chrome", "Chromium", "Microsoft Edge", "Brave Browser"]


class UiError(RuntimeError):
    """A UI command cannot do its job; the message says what the owner can do."""


@dataclass
class Screen:
    """One `### S-01 — name` entry of design/UI.md."""

    id: str
    title: str
    fields: Dict[str, str] = field(default_factory=dict)


def toolkit_dir() -> Path:
    return Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------- reading

def read(root: Path) -> Optional[str]:
    path = root / UI_FILE
    return path.read_text(encoding="utf-8") if path.is_file() else None


def surface(text: str) -> str:
    match = re.search(r"^Surface:[ \t]*(.*)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def has_no_interface(text: str) -> bool:
    """True when the record states that nobody looks at the product."""
    return surface(text).lower().rstrip(".") == "none"


def screens(text: str) -> List[Screen]:
    """The numbered screens, in the order written. Entries with a malformed heading are left to the lint."""
    found = []
    for block in re.split(r"^### ", lint._sections(text).get("Screens", ""), flags=re.MULTILINE)[1:]:
        head = re.match(r"(S-\d{2,3}) — (.*)", block.splitlines()[0])
        if not head:
            continue
        fields = {match.group(1): match.group(2).strip()
                  for match in re.finditer(r"^(\w+):[ \t]*(.*)$", block, flags=re.MULTILINE)}
        found.append(Screen(head.group(1), head.group(2).strip(), fields))
    return found


def viewport(mockup: str) -> Tuple[int, int]:
    """Width and height a mockup declares in its `devpipe-viewport` meta tag."""
    match = re.search(r'<meta\s+name=["\']devpipe-viewport["\']\s+content=["\'](\d+)\s*x\s*(\d+)["\']', mockup, flags=re.IGNORECASE)
    return (int(match.group(1)), int(match.group(2))) if match else DEFAULT_VIEWPORT


def mockups(root: Path) -> List[Path]:
    """Every mockup file, variants included (`S-01-list.html`, `S-01-list--empty.html`), in name order."""
    found = [path for path in (root / UI_DIR).glob("S-*.html") if re.match(r"S-\d{2,3}-", path.name)]
    # A screen's main file before its variants: "S-01-list" sorts ahead of "S-01-list--empty".
    return sorted(found, key=lambda path: (path.stem.split("--")[0], path.stem))


# ------------------------------------------------------------------ creating

def init(root: Path) -> List[str]:
    """Copy the record and token templates into the project where they are missing."""
    written = []
    for source, target in ((toolkit_dir() / "templates/design/UI.md", root / UI_FILE),
                           (toolkit_dir() / "templates/ui/tokens.css", root / UI_DIR / "tokens.css")):
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            written.append(str(target.relative_to(root)))
    return written


def index(root: Path) -> Path:
    """Write `design/ui/index.html`: every mockup in a frame of its own size, with its status."""
    text = read(root) or ""
    known = {screen.id: screen for screen in screens(text)}
    groups: Dict[str, List[Path]] = {}
    for path in mockups(root):
        groups.setdefault(path.name[:path.name.index("-", 2)], []).append(path)
    parts = []
    for screen_id, files in groups.items():
        screen = known.get(screen_id)
        status = screen.fields.get("Status", "") if screen else "not in design/UI.md"
        frames = []
        for path in files:
            width, height = viewport(path.read_text(encoding="utf-8", errors="replace"))
            scale = min(1.0, 640 / width)
            frames.append(
                f'<figure><div class="frame" style="width:{width * scale:.0f}px;height:{height * scale:.0f}px">'
                f'<iframe src="{html.escape(path.name)}" style="width:{width}px;height:{height}px;'
                f'transform:scale({scale:.4f})" title="{html.escape(path.stem)}"></iframe></div>'
                f'<figcaption><a href="{html.escape(path.name)}">{html.escape(path.name)}</a> · {width}×{height}</figcaption></figure>')
        title = html.escape(f"{screen_id} — {screen.title}" if screen else screen_id)
        parts.append(f'<section><h2>{title} <span class="status {html.escape(status.lower())}">{html.escape(status)}</span></h2>'
                     f'<div class="frames">{"".join(frames)}</div></section>')
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>UI mockups</title>
<style>
  body {{ margin: 0; padding: 24px 32px 64px; background: #ececec; color: #1c1c1c; font: 15px/1.4 system-ui, sans-serif; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  p.note {{ margin: 0 0 24px; color: #5c5c5c; }}
  h2 {{ font-size: 16px; margin: 32px 0 12px; }}
  .status {{ font-size: 11px; font-weight: 600; letter-spacing: .04em; padding: 2px 8px; border-radius: 10px; background: #d9d9d9; vertical-align: 2px; }}
  .status.accepted {{ background: #cfe8d2; }}
  .status.proposed {{ background: #f6e2b3; }}
  .frames {{ display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }}
  figure {{ margin: 0; }}
  .frame {{ overflow: hidden; background: #fff; box-shadow: 0 1px 6px rgba(0, 0, 0, .25); }}
  iframe {{ border: 0; transform-origin: 0 0; display: block; }}
  figcaption {{ margin-top: 6px; font-size: 12px; color: #5c5c5c; }}
</style>
</head>
<body>
<h1>UI mockups</h1>
<p class="note">Written by <code>devpipe ui index</code> from design/ui/ and design/UI.md; do not edit. {len(groups)} screen(s).</p>
{"".join(parts) or "<p>No mockup yet: design/ui/S-01-name.html is the first.</p>"}
</body>
</html>
"""
    target = root / UI_DIR / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    return target


# ----------------------------------------------------------------- rendering

def find_renderer() -> Tuple[str, str]:
    """(kind, program) of what can turn a mockup into a PNG here: chrome, firefox or webkit.

    Raises UiError when nothing can; the gallery can still be opened in a browser by hand.
    """
    named = os.environ.get("DEVPIPE_BROWSER", "")
    if named:
        return ("firefox" if "firefox" in Path(named).name.lower() else "chrome"), named
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return "chrome", found
    if platform.system() == "Darwin":
        for app in MAC_CHROME_APPS:
            binary = Path(f"/Applications/{app}.app/Contents/MacOS/{app}")
            if binary.is_file():
                return "chrome", str(binary)
    firefox = shutil.which("firefox") or (
        "/Applications/Firefox.app/Contents/MacOS/firefox"
        if Path("/Applications/Firefox.app/Contents/MacOS/firefox").is_file() else "")
    if firefox:
        return "firefox", firefox
    if platform.system() == "Darwin" and shutil.which("swift"):
        return "webkit", shutil.which("swift") or "swift"
    raise UiError("nothing here can render a page to a picture: install Chrome, Chromium or Firefox (or, on a Mac, "
                  "the Xcode command line tools), or set DEVPIPE_BROWSER to a Chrome-family binary. "
                  "The mockups can still be looked at with `devpipe ui open`.")


def shoot(source: str, width: int, height: int, target: Path, scale: int = 2) -> None:
    """Write one picture of `source`, a local file or an http(s) address, at `width` x `height` CSS pixels."""
    kind, program = find_renderer()
    remote = bool(re.match(r"https?://", source))
    address = source if remote else Path(source).resolve().as_uri()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    if kind == "chrome":
        command = [program, "--headless", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                   f"--window-size={width},{height}", f"--screenshot={target}", address]
    elif kind == "firefox":
        command = [program, "--headless", f"--window-size={width},{height}", "--screenshot", str(target), address]
    else:
        command = [program, str(toolkit_dir() / "helpers" / "webkit-shot.swift"),
                   source if remote else str(Path(source).resolve()), str(width), str(height), str(target), str(scale)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=RENDER_TIMEOUT_S, stdin=subprocess.DEVNULL)
        detail = (done.stderr or done.stdout).strip()[-300:]
    except subprocess.TimeoutExpired:
        detail = f"no picture after {RENDER_TIMEOUT_S} s"
    except OSError as error:
        detail = str(error)
    if not target.is_file() or target.stat().st_size == 0:
        raise UiError(f"{Path(source).name if not remote else source} was not rendered ({kind}): {detail or 'no output'}")


def render(root: Path, wanted: Optional[List[str]] = None, scale: int = 2) -> List[Path]:
    """Render mockups to `design/ui/renders/<name>.png`; `wanted` filters by screen id (S-01).

    Each picture has the size the mockup declares, times `scale`.
    """
    chosen = [path for path in mockups(root)
              if not wanted or any(path.name.startswith(screen_id + "-") or path.stem == screen_id for screen_id in wanted)]
    if not chosen:
        raise UiError("no mockup matches: " + (", ".join(wanted) if wanted else f"{UI_DIR}/ holds no S-*.html file"))
    written = []
    for path in chosen:
        width, height = viewport(path.read_text(encoding="utf-8", errors="replace"))
        target = root / RENDER_DIR / f"{path.stem}.png"
        shoot(str(path), width, height, target, scale)
        written.append(target)
    return written


def _split(start: int, end: int, lines: List[str], limit: int = 120) -> List[Tuple[int, int]]:
    """Cut the 1-based line range into pieces of at most about `limit` lines, at the end of a CSS rule."""
    if end - start + 1 <= limit:
        return [(start, end)]
    middle = (start + end) // 2
    cut = next((number for number in range(middle, end) if lines[number - 1].strip() in ("}", "")), middle)
    return _split(start, cut, lines, limit) + _split(cut + 1, end, lines, limit)


def parts(root: Path, screen_id: str, counter: Any) -> List[str]:
    """Describe a screen's mockup as line ranges with their sizes, ready to copy into a ticket's `read:`.

    A ticket cannot afford a whole mockup, and an agent that has to find the ranges itself
    spends a dozen steps on `wc` and `sed`.
    """
    files = [path for path in mockups(root) if path.name.startswith(screen_id + "-")]
    if not files:
        raise UiError(f"no mockup for {screen_id} under {UI_DIR}/")
    main = files[0]
    relative = str(main.relative_to(root))
    lines = main.read_text(encoding="utf-8", errors="replace").splitlines()

    def find(opening: str, closing: str) -> Optional[Tuple[int, int]]:
        first = next((number for number, line in enumerate(lines, start=1) if opening in line.lower()), 0)
        last = next((number for number, line in enumerate(lines, start=1) if number >= first and closing in line.lower()), 0)
        return (first, last or len(lines)) if first else None

    def size(first: int, last: int) -> str:
        count, _exact = counter.count("\n".join(lines[first - 1:last]))
        return f"{count} tokens"

    whole, exact = counter.count("\n".join(lines))
    style, body = find("<style", "</style>"), find("<body", "</body>")
    rules = _split(style[0], style[1], lines) if style else []
    out = [f"{relative}: {len(lines)} lines, {whole} tokens" + ("" if exact else " (estimate)")]
    for first, last in rules:
        out.append(f"  layout rules  lines {first}-{last}  {size(first, last)}")
    if body:
        out.append(f"  the screen    lines {body[0]}-{body[1]}  {size(body[0], body[1])}")
    if len(files) > 1:
        out.append("  other states: " + ", ".join(path.name for path in files[1:]))

    def entry(first: int, last: int) -> str:
        return f'  - {{path: {relative}, lines: "{first}-{last}"}}'

    section = f'  - {{path: {UI_FILE}, section: "{screen_id}"}}'
    out.append("read entries for the ticket that builds this screen's layout:")
    out += [entry(first, last) for first, last in rules] + ([entry(*body)] if body else []) + [section]
    out.append("read entries for any other ticket of this screen:")
    out += ([entry(*body)] if body else []) + [section]
    return out


def compare(root: Path, screen_id: str, built: str = "", scale: int = 1) -> Tuple[Path, Path]:
    """Put the built screen beside its mockup: returns (page, picture) under `.tickets/.work/ui-compare/`.

    `built` (or the screen's `Built:` line) says where the built screen is: an http address,
    a file (HTML, or a screenshot the project's own tests made), or `run <command>` whose
    output is the screen's HTML. The picture shows mockup, built screen and their
    difference, so one look, by the owner or by a model that reads images, settles it.
    """
    screen = next((entry for entry in screens(read(root) or "") if entry.id == screen_id), None)
    if screen is None:
        raise UiError(f"design/UI.md has no screen {screen_id}")
    mockup = root / screen.fields.get("Mockup", "")
    if not mockup.is_file():
        raise UiError(f"{screen_id}: mockup {screen.fields.get('Mockup', '(none)')} does not exist")
    source = (built or screen.fields.get("Built", "")).strip()
    if not source or source.lower().startswith("not yet"):
        raise UiError(f"{screen_id} has no 'Built:' line in design/UI.md saying where the built screen is "
                      "(an http address, a file, or `run <command>` that prints its HTML); or pass --built")
    width, height = viewport(mockup.read_text(encoding="utf-8", errors="replace"))
    out = root / COMPARE_DIR
    out.mkdir(parents=True, exist_ok=True)
    mockup_picture, built_picture = out / f"{screen_id}-mockup.png", out / f"{screen_id}-built.png"
    shoot(str(mockup), width, height, mockup_picture, scale)
    if source.startswith("run "):
        command = source[4:].strip()
        done = subprocess.run(command, shell=True, cwd=str(root), capture_output=True, text=True,
                              timeout=RENDER_TIMEOUT_S, stdin=subprocess.DEVNULL)
        if done.returncode != 0 or not done.stdout.strip():
            raise UiError(f"`{command}` did not print the built screen (exit {done.returncode}): {done.stderr.strip()[-200:]}")
        page = out / f"{screen_id}-built.html"
        page.write_text(done.stdout, encoding="utf-8")
        shoot(str(page), width, height, built_picture, scale)
    elif re.match(r"https?://", source):
        shoot(source, width, height, built_picture, scale)
    else:
        path = root / source
        if not path.is_file():
            raise UiError(f"{screen_id}: built screen {source} does not exist")
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            shutil.copyfile(path, built_picture)   # a screenshot from the project's own tests
        else:
            shoot(str(path), width, height, built_picture, scale)

    shown = min(width, 520)
    tall = round(height * shown / width)
    box = f"width:{shown}px;height:{tall}px"
    page = out / f"{screen_id}.html"
    page.write_text(f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(screen_id)} mockup and built</title>
<style>
  body {{ margin: 0; padding: 20px 24px; background: #ececec; color: #1c1c1c; font: 14px/1.4 system-ui, sans-serif; }}
  h1 {{ font-size: 17px; margin: 0 0 14px; }}
  .row {{ display: flex; gap: 24px; }}
  figure {{ margin: 0; }}
  img {{ display: block; background: #fff; }}
  .frame {{ box-shadow: 0 1px 6px rgba(0, 0, 0, .25); }}
  .difference {{ position: relative; background: #000; }}
  .difference img {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
  .difference img + img {{ mix-blend-mode: difference; }}
  figcaption {{ margin-top: 6px; font-size: 12px; color: #5c5c5c; max-width: {shown}px; }}
</style>
</head>
<body>
<h1>{html.escape(screen_id)} — {html.escape(screen.title)}</h1>
<div class="row">
<figure><img class="frame" src="{mockup_picture.name}" style="{box}" alt="mockup"><figcaption>Mockup · {html.escape(screen.fields.get('Mockup', ''))}</figcaption></figure>
<figure><img class="frame" src="{built_picture.name}" style="{box}" alt="built"><figcaption>Built · {html.escape(source[:90])}</figcaption></figure>
<figure><div class="frame difference" style="{box}"><img src="{mockup_picture.name}" alt=""><img src="{built_picture.name}" alt=""></div><figcaption>Difference · black where the two agree</figcaption></figure>
</div>
</body>
</html>
""", encoding="utf-8")
    picture = out / f"{screen_id}.png"
    shoot(str(page), 3 * shown + 4 * 24, tall + 110, picture, 1)
    return page, picture


def with_built(root: Path) -> List[str]:
    """Ids of the screens whose `Built:` line names something to look at."""
    return [screen.id for screen in screens(read(root) or "")
            if screen.fields.get("Built", "").strip() and not screen.fields["Built"].lower().startswith("not yet")]


def open_gallery(root: Path) -> Path:
    """Rebuild the gallery page and open it in the default browser."""
    page = index(root)
    opener = "open" if platform.system() == "Darwin" else "xdg-open"
    if not shutil.which(opener):
        raise UiError(f"`{opener}` is not available here; open {page} in a browser yourself")
    subprocess.run([opener, str(page)], check=False, stdin=subprocess.DEVNULL)
    return page


def serve(root: Path, host: str, port: int) -> None:
    """Serve `design/ui/` over HTTP until interrupted, for a browser on this or another machine."""
    index(root)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root / UI_DIR))
    with http.server.ThreadingHTTPServer((host, port), handler) as server:
        print(f"devpipe: serving {UI_DIR}/ at http://{host}:{port}/ ; stop with Ctrl-C", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("devpipe: stopped serving", flush=True)


# ---------------------------------------------------------------------- lint

def lint_ui(root: Path, allow_open: bool = False) -> List[lint.Issue]:
    """Check the UI record: sections, screens, mockups, tokens, tooling, and that the owner accepted each screen."""
    issues: List[lint.Issue] = []
    where = UI_FILE

    def error(place: str, message: str) -> None:
        issues.append(lint.Issue(lint.ERROR, place, message))

    text = read(root)
    if text is None:
        error(where, "file is missing; the ui-design stage writes it (for a product nobody looks at it records just that)")
        return issues
    if not surface(text):
        error(where, "'Surface:' line is missing; it names what the interface runs on, or says 'none'")
        return issues
    if has_no_interface(text):
        if not re.search(r"^Reason:[ \t]*\S", text, flags=re.MULTILINE):
            error(where, "'Surface: none' needs a line 'Reason: …' saying why the product has no interface")
        return issues

    sections = lint._sections(text)
    for name in SECTIONS:
        if name not in sections:
            error(where, f"section '## {name}' is missing")
    lint._placeholders(text, where, issues)
    if "Not yet decided" in sections and not lint._is_empty_section(sections["Not yet decided"]):
        issues.append(lint.Issue(lint.WARN if allow_open else lint.ERROR, where,
                                 "'Not yet decided' still lists open items; settle them with the owner or write 'None.'"))
    if lint._is_empty_section(sections.get("Accessibility", "x")):
        error(where, "'## Accessibility' is empty; state the contrast target, target sizes and text scaling at least")

    spec_path = root / "design" / "SPECIFICATION.md"
    defined = set(lint.requirement_ids(spec_path.read_text(encoding="utf-8"))) if spec_path.is_file() else set()
    blocks = re.split(r"^### ", sections.get("Screens", ""), flags=re.MULTILINE)[1:]
    if not blocks:
        error(where, "no screen found; each one starts with '### S-01 — name'")
    seen: Dict[str, str] = {}
    for block in blocks:
        title = block.splitlines()[0]
        head = re.match(r"(S-\d{2,3}) — \S", title)
        if not head:
            error(where, f"screen heading {title!r} must read 'S-01 — name'")
            continue
        screen_id = head.group(1)
        if screen_id in seen:
            error(where, f"{screen_id} is defined twice")
        seen[screen_id] = title
    for screen in screens(text):
        label = f"{where} {screen.id}"
        for name in SCREEN_FIELDS:
            if not screen.fields.get(name):
                error(label, f"'{name}:' is missing or empty")
        serves = screen.fields.get("Serves", "")
        cited = set(re.findall(r"R-\d{3}", serves))
        if serves and not cited and serves.lower().rstrip(".") != "none":
            error(label, "'Serves:' lists requirement ids (R-001, …) or says none")
        for name in sorted(cited - defined) if defined else []:
            error(label, f"{name} is not defined in design/SPECIFICATION.md")
        status = screen.fields.get("Status", "")
        if status == "PROPOSED":
            issues.append(lint.Issue(lint.WARN if allow_open else lint.ERROR, label,
                                     "is still PROPOSED; it becomes ACCEPTED when the owner has seen its mockup and said so"))
        elif status and status != "ACCEPTED":
            error(label, f"status {status!r} must be PROPOSED or ACCEPTED")
        mockup = screen.fields.get("Mockup", "")
        if not mockup:
            continue
        path = root / mockup
        if not mockup.startswith(UI_DIR + "/") or not path.name.startswith(screen.id + "-") or path.suffix != ".html":
            error(label, f"'Mockup:' must be {UI_DIR}/{screen.id}-<name>.html")
        elif not path.is_file():
            error(label, f"mockup {mockup} does not exist")
        else:
            _lint_mockup(path, mockup, issues)

    tokens = root / UI_DIR / "tokens.css"
    if not tokens.is_file():
        error(f"{UI_DIR}/tokens.css", "file is missing; the mockups and the product's theme take their values from it")
    else:
        lint._placeholders(tokens.read_text(encoding="utf-8"), f"{UI_DIR}/tokens.css", issues, blanks_only=True)

    stack_path = root / "design" / "STACK.md"
    stack = lint.stack_names(stack_path.read_text(encoding="utf-8")) if stack_path.is_file() else set()
    tools = lint.stack_names(sections.get("Tooling", ""))
    if not tools:
        error(where, "'## Tooling' names no tool; the table is | Name | Role |")
    for name in sorted(tools - stack) if stack else []:
        error(where, f"tool {name!r} is not in design/STACK.md; adding it there, pinned, is the owner's decision")
    return issues


def _lint_mockup(path: Path, shown: str, issues: List[lint.Issue]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not re.search(r'<meta\s+name=["\']devpipe-viewport["\']\s+content=["\']\d+\s*x\s*\d+["\']', text, flags=re.IGNORECASE):
        issues.append(lint.Issue(lint.ERROR, shown, "needs <meta name=\"devpipe-viewport\" content=\"WIDTHxHEIGHT\"> "
                                                    "so it is shown and rendered at the size it was designed for"))
    remote = re.search(r'(?:src|href)\s*=\s*["\']https?://[^"\']+|url\(\s*["\']?https?://[^)"\']+', text, flags=re.IGNORECASE)
    if remote:
        issues.append(lint.Issue(lint.ERROR, shown, f"loads from the network ({remote.group(0)[:60]}); a mockup carries "
                                                    "everything it shows, so it looks the same offline and next year"))
    lint._placeholders(text, shown, issues, blanks_only=True)
    if "tokens.css" not in text:
        issues.append(lint.Issue(lint.WARN, shown, "does not link tokens.css; its colours and sizes will drift from the others"))


def lint_coverage(root: Path) -> List[lint.Issue]:
    """Check DEV_PLAN.md against the UI record: every screen is built by a step, and no step names an unknown one."""
    plan_path = root / "DEV_PLAN.md"
    if not plan_path.is_file():
        return []
    text = read(root)
    if text is None:
        return [lint.Issue(lint.WARN, UI_FILE, "file is missing, so nothing checks that the plan builds an interface anyone "
                                               "designed; the ui-design stage writes it")]
    if has_no_interface(text):
        return []
    issues = []
    known = {screen.id: screen.title for screen in screens(text)}
    built = set()
    for steps in lint.plan_steps(plan_path.read_text(encoding="utf-8")).values():
        for step_id, _title, block in steps:
            named = re.search(r"^- Screens:(.*)$", block, flags=re.MULTILINE)
            for screen_id in re.findall(r"S-\d{2,3}", named.group(1)) if named else []:
                built.add(screen_id)
                if screen_id not in known:
                    issues.append(lint.Issue(lint.ERROR, f"DEV_PLAN.md step {step_id}",
                                             f"builds {screen_id}, which design/UI.md does not define"))
    for screen_id in sorted(set(known) - built):
        issues.append(lint.Issue(lint.ERROR, "DEV_PLAN.md", f"{screen_id} ({known[screen_id]}) is not built by any step; "
                                                            "name it on a step's '- Screens:' line"))
    return issues
