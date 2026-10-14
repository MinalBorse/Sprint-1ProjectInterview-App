"""Record a demo video of a Streamlit app, driven by a scene file.

Command 1 of 2:
    python scripts/record_demo.py --scenes demo/scenes.json --out demo/output

What it does:
  1. Checks the scene file against the app code (see check_scenes.py).
  2. Starts the Streamlit app in the background, on a free port, with a clean
     temporary folder for any database or data files.
  3. Opens a 1920x1080 browser with Playwright, and records the screen.
  4. Plays each scene: shows its caption, highlights and performs each action,
     and waits for result text to appear (never a fixed guess of how long).
  5. Saves raw_recording.webm, plus timings.json: the exact moment each caption
     appeared, and the start and end of every long wait marked "cut".

Then run scripts/add_voiceover.py to add the narration and export the videos.
This file is identical in every project: only demo/scenes.json changes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from string import Template

from playwright.sync_api import Locator, Page, sync_playwright

# Import the checker from the same folder, whatever folder we're run from.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_scenes  # noqa: E402

VIEWPORT = {"width": 1920, "height": 1080}

# How long to wait for things, in milliseconds.
UI_TIMEOUT_MS = 15_000  # buttons, tabs and boxes should appear quickly
AI_TIMEOUT_MS = 180_000  # an AI reply can take minutes on a slow day
APPEAR_GRACE_MS = 5_000  # how long a spinner gets to show up (see wait_gone)

# When a long wait is cut, keep a little of it, so the viewer still sees the
# spinner start and the result arrive, rather than an abrupt jump.
CUT_KEEP_HEAD_MS = 700
CUT_KEEP_TAIL_MS = 500
MIN_CUT_MS = 1_500  # waits shorter than this aren't worth cutting

# A typical neural voice speaks about 2.6 words per second at normal rate.
# Used to keep each scene on screen long enough for its narration.
WORDS_PER_SECOND = 2.6
HIGHLIGHT_MS = 450  # how long the highlight shows before the action happens


# =============================================================================
# Starting and stopping the app
# =============================================================================


def free_port() -> int:
    """Ask the operating system for a port nobody is using."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def build_env(app_cfg: dict, tmp_dir: Path) -> dict:
    """The environment for the app: your normal one, plus the scene file's env block.

    Values can use ${TMP_DIR} (a fresh, empty folder for this recording, so
    the demo always starts from a clean database) and ${ANY_VARIABLE} from
    your own environment, like an API key.
    """
    env = dict(os.environ)
    env["TMP_DIR"] = str(tmp_dir)
    for name, value in app_cfg.get("env", {}).items():
        env[name] = Template(str(value)).safe_substitute(env)
    return env


def start_app(
    app_cfg: dict, root: Path, out_dir: Path, tmp_dir: Path
) -> tuple[subprocess.Popen, str]:
    """Start Streamlit in the background, and return the process and its URL."""
    port = free_port()
    command = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_cfg.get("entry", "app.py"),
        "--server.port",
        str(port),
        "--server.headless",
        "true",  # don't open a browser of its own
        "--browser.gatherUsageStats",
        "false",
        "--server.runOnSave",
        "false",
    ]
    log = open(out_dir / "streamlit.log", "w", encoding="utf-8")  # noqa: SIM115
    process = subprocess.Popen(
        command,
        cwd=root,
        env=build_env(app_cfg, tmp_dir),
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    wait_for_server(url, process)
    return process, url


def wait_for_server(url: str, process: subprocess.Popen, timeout_s: int = 90) -> None:
    """Poll Streamlit's health check until it answers, or fail with a clear message."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "The app stopped while starting: see streamlit.log in the output folder"
            )
        for path in ("/_stcore/health", "/healthz"):  # new and old Streamlit versions
            try:
                with urllib.request.urlopen(url + path, timeout=2) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, OSError):
                pass
        time.sleep(0.5)
    raise RuntimeError(f"The app didn't start within {timeout_s} seconds")


def stop_app(process: subprocess.Popen) -> None:
    """Stop the app politely, then firmly if it doesn't listen."""
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


# =============================================================================
# Small pieces of JavaScript, run inside the page
# =============================================================================

# The caption overlay. It's added to <body>, outside Streamlit's own area, so
# Streamlit's reruns don't remove it. We still recreate it if it's missing.
CAPTION_JS = """(text) => {
  let box = document.getElementById('demo-caption');
  if (!box) {
    box = document.createElement('div');
    box.id = 'demo-caption';
    Object.assign(box.style, {
      position: 'fixed', left: '50%', bottom: '48px', transform: 'translateX(-50%)',
      maxWidth: '80%', padding: '18px 34px', borderRadius: '14px',
      background: 'rgba(0, 0, 0, 0.78)', color: '#fff', zIndex: '2147483647',
      font: '600 34px/1.35 system-ui, -apple-system, Segoe UI, sans-serif',
      textAlign: 'center', boxShadow: '0 8px 30px rgba(0, 0, 0, 0.35)',
      transition: 'opacity 250ms', pointerEvents: 'none',
    });
    document.body.appendChild(box);
  }
  box.textContent = text;
  box.style.opacity = '1';
}"""

# The visible page text, without our own caption. We read innerText rather than
# searching elements, because innerText only includes text that is actually
# shown: text in a hidden tab doesn't count, which is exactly what we want.
VISIBLE_TEXT_JS = """() => {
  const caption = document.getElementById('demo-caption');
  let text = document.body.innerText;
  if (caption && caption.innerText) text = text.split(caption.innerText).join('');
  return text;
}"""

HAS_TEXT_JS = "(t) => (" + VISIBLE_TEXT_JS + ")().includes(t)"
LACKS_TEXT_JS = "(t) => !(" + VISIBLE_TEXT_JS + ")().includes(t)"

# Find the visible element that contains some text, and scroll it to the middle
# of the screen, with a highlight so the viewer's eye follows.
SCROLL_TO_TEXT_JS = """(t) => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const el = walker.currentNode.parentElement;
    if (!el || el.closest('#demo-caption')) continue;
    if (walker.currentNode.textContent.includes(t) && el.offsetParent !== null) {
      el.scrollIntoView({behavior: 'smooth', block: 'center'});
      el.style.outline = '4px solid #f5a623';
      el.style.outlineOffset = '4px';
      setTimeout(() => { el.style.outline = ''; }, 1500);
      return true;
    }
  }
  return false;
}"""

HIGHLIGHT_ON_JS = """(el) => {
  el.dataset.demoOutline = el.style.outline || '';
  el.style.outline = '4px solid #f5a623';
  el.style.outlineOffset = '4px';
  el.style.borderRadius = el.style.borderRadius || '8px';
}"""
HIGHLIGHT_OFF_JS = "(el) => { el.style.outline = el.dataset.demoOutline || ''; }"


# =============================================================================
# Playing the scenes
# =============================================================================


class Recorder:
    """Plays scenes in the page, and keeps track of every timestamp."""

    def __init__(self, page: Page, video_start: float, out_dir: Path):
        self.page = page
        self.video_start = video_start  # time.monotonic() when recording began
        self.out_dir = out_dir
        self.captions: list[dict] = []
        self.cuts: list[dict] = []

    def now_ms(self) -> int:
        """Milliseconds since the video started recording."""
        return int((time.monotonic() - self.video_start) * 1000)

    # ----- Captions and highlights -----

    def show_caption(self, scene: dict) -> None:
        self.page.evaluate(CAPTION_JS, scene["caption"])
        # The narration for this scene will be placed at exactly this moment,
        # so the voice and the caption always start together.
        self.captions.append(
            {
                "id": scene["id"],
                "caption_ms": self.now_ms(),
                "caption": scene["caption"],
            }
        )

    def highlight(self, target: Locator) -> None:
        """Scroll to an element and outline it briefly, before acting on it.

        A recording has no visible mouse pointer, so without this the viewer
        wouldn't know what was clicked.
        """
        target.scroll_into_view_if_needed(timeout=UI_TIMEOUT_MS)
        try:
            target.evaluate(HIGHLIGHT_ON_JS)
            self.page.wait_for_timeout(HIGHLIGHT_MS)
            target.evaluate(HIGHLIGHT_OFF_JS)
        except Exception:
            pass  # the element may be redrawn by Streamlit: the highlight is only cosmetic

    # ----- Waiting for text, in sync with the app -----

    def wait_for(self, js: str, text: str, timeout_ms: int) -> None:
        """Wait until the page's visible text passes a check.

        Why this, instead of fixed delays like "wait 10 seconds"? An AI reply
        can take 3 seconds or 60. A fixed delay is either too short (the video
        moves on before the answer appears) or wastes time. Waiting for the
        actual text keeps the recording in step with the app, however slow the
        AI is that day; the long waits are then cut out afterwards.
        """
        self.page.wait_for_function(js, arg=text, timeout=timeout_ms, polling=200)

    def timed_wait(self, action: dict, scene_id: str, js: str, timeout_ms: int) -> int:
        """Run a wait, and if it's marked cut, record which part to remove.

        Returns how many milliseconds will be cut, so the scene's narration
        timing can allow for them.
        """
        start = self.now_ms()
        if action["type"] == "wait_gone":
            # A spinner might not have appeared yet when we start checking; if we
            # only waited for it to be gone, we'd "succeed" before the work began.
            # So first give it a moment to show up, then wait for it to go.
            try:
                self.wait_for(HAS_TEXT_JS, action["text"], APPEAR_GRACE_MS)
            except Exception:
                pass  # it may have come and gone already: that's fine
        self.wait_for(js, action["text"], timeout_ms)
        end = self.now_ms()

        if not action.get("cut"):
            return 0
        cut_start, cut_end = start + CUT_KEEP_HEAD_MS, end - CUT_KEEP_TAIL_MS
        if cut_end - cut_start < MIN_CUT_MS:
            return 0
        self.cuts.append({"scene": scene_id, "start_ms": cut_start, "end_ms": cut_end})
        return cut_end - cut_start

    # ----- The actions -----

    def run_action(self, action: dict, scene_id: str) -> int:
        """Perform one action. Returns the milliseconds that will be cut."""
        page, atype = self.page, action["type"]
        timeout = int(action.get("timeout_s", 0) * 1000) or None

        if atype == "click_button":
            target = page.get_by_role("button", name=action["label"]).first
            self.highlight(target)
            target.click(timeout=UI_TIMEOUT_MS)

        elif atype == "click_tab":
            target = page.get_by_role("tab", name=action["label"]).first
            self.highlight(target)
            target.click(timeout=UI_TIMEOUT_MS)

        elif atype == "select":
            self.select_option(action)

        elif atype == "fill":
            target = page.get_by_label(action["label"], exact=True).first
            self.highlight(target)
            target.fill(action["text"], timeout=UI_TIMEOUT_MS)
            # Streamlit only takes the new value when the box loses focus.
            target.evaluate("(el) => el.blur()")
            page.wait_for_timeout(300)

        elif atype == "type_chat":
            box = page.locator('[data-testid="stChatInputTextArea"]').first
            if action.get("placeholder"):
                box = page.get_by_placeholder(action["placeholder"]).first
            self.highlight(box)
            # Typing letter by letter looks natural on video; long texts are pasted.
            delay = 25 if len(action["text"]) <= 160 else 0
            box.press_sequentially(action["text"], delay=delay, timeout=UI_TIMEOUT_MS)
            box.press("Enter")

        elif atype == "scroll_to":
            self.wait_for(HAS_TEXT_JS, action["text"], timeout or UI_TIMEOUT_MS)
            page.evaluate(SCROLL_TO_TEXT_JS, action["text"])
            page.wait_for_timeout(900)  # let the smooth scroll finish on screen

        elif atype == "wait_text":
            return self.timed_wait(
                action, scene_id, HAS_TEXT_JS, timeout or AI_TIMEOUT_MS
            )

        elif atype == "wait_gone":
            return self.timed_wait(
                action, scene_id, LACKS_TEXT_JS, timeout or AI_TIMEOUT_MS
            )

        elif atype == "pause":
            page.wait_for_timeout(int(action["ms"]))  # deliberate pacing, not syncing

        else:
            raise ValueError(f"Unknown action type: {atype}")
        return 0

    def select_option(self, action: dict) -> None:
        """Choose a dropdown option by typing part of it, then taking the first match.

        Why not click the option by its exact text? Option labels built from data
        can contain characters that are hard to match exactly (quotes, emoji,
        non-breaking spaces, trailing spaces). Typing a simple part of the option
        uses the dropdown's own filter, which is far more forgiving.
        """
        page = self.page
        # The typing box of a Streamlit dropdown is a "combobox" named after the
        # label. Finding it by that role, rather than by Streamlit's internal
        # class names, keeps working when Streamlit changes how it draws
        # dropdowns (it has, between versions).
        combo = page.get_by_role("combobox", name=action["label"]).first
        container = combo.locator("xpath=ancestor::*[@data-testid='stSelectbox'][1]")
        self.highlight(container if container.count() else combo)
        combo.click(timeout=UI_TIMEOUT_MS)
        # Select whatever is already in the box, so only our filter text is typed.
        combo.press("ControlOrMeta+a")
        page.keyboard.type(action["option"], delay=40)
        option = page.get_by_role("option").first
        option.wait_for(state="visible", timeout=UI_TIMEOUT_MS)
        option.click()
        page.wait_for_timeout(300)

    # ----- A whole scene -----

    def play(self, scene: dict) -> None:
        """Show the caption, run the actions, then keep the scene on screen long
        enough for its narration to be spoken."""
        started = self.now_ms()
        self.show_caption(scene)
        cut_ms = 0
        for action in scene.get("actions", []):
            cut_ms += self.run_action(action, scene["id"])

        # Estimate how long the narration will take, and stay on this scene at
        # least that long. Time that will be cut doesn't count as screen time.
        words = len(scene["voice"].split())
        needed_ms = int(words / WORDS_PER_SECOND * 1000) + int(
            scene.get("hold_ms", 600)
        )
        shown_ms = self.now_ms() - started - cut_ms
        if shown_ms < needed_ms:
            self.page.wait_for_timeout(needed_ms - shown_ms)

    def save_timings(self, failed_scene: str | None = None) -> None:
        data = {
            "video": "raw_recording.webm",
            "viewport": VIEWPORT,
            "captions": self.captions,
            "cuts": self.cuts,
            "end_ms": self.now_ms(),
            "failed_scene": failed_scene,
        }
        (self.out_dir / "timings.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record a demo video from demo/scenes.json."
    )
    parser.add_argument("--scenes", default="demo/scenes.json", type=Path)
    parser.add_argument("--out", default="demo/output", type=Path)
    parser.add_argument("--app-dir", default=".", type=Path, help="the project folder")
    parser.add_argument(
        "--headed", action="store_true", help="show the browser while recording"
    )
    parser.add_argument(
        "--skip-check", action="store_true", help="don't check the scene file first"
    )
    args = parser.parse_args()

    root = args.app_dir.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Check the scene file first, so a typo doesn't waste a recording.
    if not args.skip_check:
        errors, warnings = check_scenes.check(args.scenes, root)
        for warning in warnings:
            print(f"  ~ {warning}")
        if errors:
            for error in errors:
                print(f"  x {error}")
            print("Scene file has errors: fix them, or use --skip-check.")
            return 1

    config = json.loads(args.scenes.read_text(encoding="utf-8"))
    app_cfg, scenes = config.get("app", {}), config["scenes"]

    tmp_dir = Path(tempfile.mkdtemp(prefix="demo_app_"))
    video_dir = Path(tempfile.mkdtemp(prefix="demo_video_"))
    process = None
    exit_code = 0

    try:
        # 2. Start the app with a clean temporary folder.
        print("Starting the app...")
        process, url = start_app(app_cfg, root, out_dir, tmp_dir)

        with sync_playwright() as playwright:
            # 3. Open the browser, recording at full HD.
            browser = playwright.chromium.launch(headless=not args.headed)
            context = browser.new_context(
                viewport=VIEWPORT,
                record_video_dir=str(video_dir),
                record_video_size=VIEWPORT,
            )
            page = context.new_page()
            # Recording starts when the page is created, so this is time zero.
            recorder = Recorder(page, time.monotonic(), out_dir)

            page.goto(url)
            page.wait_for_function(
                HAS_TEXT_JS, arg=app_cfg["ready_text"], timeout=60_000
            )

            current = None
            try:
                # 4. Play every scene.
                for number, scene in enumerate(scenes, start=1):
                    current = scene["id"]
                    print(f"  [{number}/{len(scenes)}] {current}")
                    recorder.play(scene)
                recorder.save_timings()
            except Exception as error:
                # 5. On failure, keep a screenshot named after the scene, so you
                # can see exactly where it stopped, and keep the partial video.
                shot = out_dir / f"failed_{current}.png"
                try:
                    page.screenshot(path=str(shot), full_page=True)
                except Exception:
                    pass
                recorder.save_timings(failed_scene=current)
                print(f"\nFailed in scene '{current}': {error}\nScreenshot: {shot}")
                exit_code = 1

            # Closing the page finishes the video file; save_as then copies it.
            video = page.video
            page.close()
            video.save_as(str(out_dir / "raw_recording.webm"))
            context.close()
            browser.close()
    finally:
        if process:
            stop_app(process)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(video_dir, ignore_errors=True)

    if exit_code == 0:
        print(f"\nDone: {out_dir / 'raw_recording.webm'} and timings.json")
        print("Next: python scripts/add_voiceover.py")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
