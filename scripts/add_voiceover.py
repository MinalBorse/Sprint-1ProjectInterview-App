"""Add narration to the recorded demo, cut the long waits, and export the videos.

Command 2 of 2 (after record_demo.py):
    python scripts/add_voiceover.py --scenes demo/scenes.json --out demo/output

Optional: --voice en-GB-SoniaNeural   --rate +5%

What it does:
  1. Cuts the long AI waits (marked "cut" in scenes.json) out of the video, in
     one streaming ffmpeg pass that never holds the whole video in memory.
  2. Turns each scene's narration into speech with edge-tts.
  3. Places each voice clip exactly when its caption appeared. A clip too long
     for its scene is sped up (only that clip, at most 1.35x).
  4. Mixes the voices over a silent base track that starts at 0 seconds.
  5. Exports demo_youtube.mp4 (1080p), demo_github.mp4 (under 10 MB) and
     subtitles.srt.

The narration text comes from scenes.json (matched by scene id), so you can
fix a sentence and rerun this script without recording again.
This file is identical in every project: only demo/scenes.json changes.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

FPS = 25  # the frame rate of the finished videos
SAMPLE_RATE = 48_000
GAP_MS = 150  # a short breath between one clip ending and the next starting
DEFAULT_MAX_SPEEDUP = 1.35  # faster than this, a voice starts to sound rushed
GITHUB_LIMIT_MB = 10.0  # GitHub plays videos up to 10 MB inline in a README


# =============================================================================
# Finding and running ffmpeg
# =============================================================================


def find_ffmpeg() -> tuple[str, str]:
    """Return the paths to ffmpeg and ffprobe.

    Uses ffmpeg from the system if it's installed. If not, falls back to the
    static-ffmpeg package, which downloads a ready-made ffmpeg the first time,
    so nobody has to install ffmpeg by hand.
    """
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    try:
        import static_ffmpeg

        print("No system ffmpeg found: using the static-ffmpeg package...")
        static_ffmpeg.add_paths()  # downloads on first use, then adds it to PATH
    except ImportError:
        sys.exit("ffmpeg not found. Install it, or: pip install static-ffmpeg")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not (ffmpeg and ffprobe):
        sys.exit(
            "static-ffmpeg couldn't provide ffmpeg. Please install ffmpeg manually."
        )
    return ffmpeg, ffprobe


def run(command: list[str], what: str) -> None:
    """Run an ffmpeg command, and show its error output only if it fails."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-3000:])
        sys.exit(f"ffmpeg failed while {what}")


def duration_s(ffprobe: str, path: Path) -> float:
    """The length of an audio or video file, in seconds."""
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


# =============================================================================
# Step 1: cutting the long waits
# =============================================================================


def map_time(ms: int, cuts: list[dict]) -> int:
    """Where a moment in the raw video ends up, after the cuts are removed.

    Every cut before this moment shifts it earlier by the cut's length. A
    moment inside a cut moves to where the cut begins.
    """
    removed = 0
    for cut in cuts:
        if ms >= cut["end_ms"]:
            removed += cut["end_ms"] - cut["start_ms"]
        elif ms > cut["start_ms"]:
            removed += ms - cut["start_ms"]
    return ms - removed


def cut_video(ffmpeg: str, raw: Path, out: Path, cuts: list[dict]) -> None:
    """Remove the cut parts of the video, in one streaming ffmpeg pass.

    Why the 'select' filter, and not trim + concat? The obvious way to cut is to
    trim each part to keep, then join them. But all the parts come from one
    input, which ffmpeg must split into several copies, and it has to hold every
    frame that a later part will need until that part's turn: on a long
    recording, that can mean gigabytes of memory. The 'select' filter instead
    looks at each frame once, as it streams past, and simply drops it if it's
    inside a cut. Memory use stays small and flat, so it runs on an 8 GB laptop.

    Why 'fps' first? Playwright records with a variable frame rate. Turning it
    into a steady rate first means that after frames are dropped, 'setpts' can
    renumber the rest evenly (frame N plays at N / FPS seconds) with no gaps.
    """
    filters = [f"fps={FPS}"]
    if cuts:
        removed = "+".join(
            f"between(t,{c['start_ms'] / 1000:.3f},{c['end_ms'] / 1000:.3f})"
            for c in cuts
        )
        filters.append(f"select='not({removed})'")
        filters.append(f"setpts=N/{FPS}/TB")
    # Make sure the result is exactly 1920x1080, whatever the recorder produced.
    filters.append("scale=1920:1080:force_original_aspect_ratio=decrease")
    filters.append("pad=1920:1080:(ow-iw)/2:(oh-ih)/2")
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(raw),
            "-vf",
            ",".join(filters),
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(out),
        ],
        "cutting the long waits",
    )


# =============================================================================
# Step 2: the narration
# =============================================================================


async def synthesize_all(clips: list[tuple[str, Path]], voice: str, rate: str) -> None:
    """Turn each scene's text into an mp3, one at a time (polite to the service)."""
    import edge_tts

    for text, path in clips:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(path))


def prepare_clip(ffmpeg: str, mp3: Path, wav: Path, tempo: float) -> None:
    """Convert a clip to 48 kHz stereo WAV, speeding it up if needed.

    'atempo' changes the speed without changing the pitch, so a sped-up voice
    still sounds natural, just a little quicker.
    """
    audio_filter = f"atempo={tempo:.4f}," if tempo > 1.001 else ""
    audio_filter += f"aresample={SAMPLE_RATE}"
    run(
        [ffmpeg, "-y", "-i", str(mp3), "-af", audio_filter, "-ac", "2", str(wav)],
        "preparing a clip",
    )


def schedule(
    captions: list[dict],
    clip_ms: dict[str, int],
    cuts: list[dict],
    video_ms: int,
    max_speedup: float,
) -> list[dict]:
    """Decide when each clip plays, and how much to speed it up.

    Each clip starts exactly when its caption appeared (moved earlier by any
    cuts before it). The space it has is until the next scene's caption.

    If a clip is too long for that space, only that clip is sped up, just
    enough to fit. The cap (1.35x by default) exists because beyond that a
    voice sounds rushed and hard to follow. If even the capped speed doesn't
    fit, the next clip waits until this one ends, so two voices never overlap:
    that next clip then starts slightly after its caption. The fix for that is
    a longer scene, with "hold_ms" in scenes.json.
    """
    plan, earliest = [], 0
    starts = [map_time(c["caption_ms"], cuts) for c in captions]
    for i, caption in enumerate(captions):
        if caption["id"] not in clip_ms:
            continue
        start = max(starts[i], earliest)
        next_start = starts[i + 1] if i + 1 < len(captions) else video_ms
        room = max(next_start - start - GAP_MS, 1)
        length = clip_ms[caption["id"]]
        if start > starts[i]:
            print(
                f"  ! '{caption['id']}': starts {(start - starts[i]) / 1000:.1f} s after its "
                "caption, because the previous clip ran long."
            )

        tempo = 1.0
        if length > room:
            tempo = min(length / room, max_speedup)
            if length / room > max_speedup:
                print(
                    f"  ! '{caption['id']}': narration is too long for its scene, even at "
                    f"{max_speedup}x. Add hold_ms to this scene in scenes.json."
                )
        played = int(length / tempo)
        plan.append(
            {
                "id": caption["id"],
                "start_ms": start,
                "tempo": tempo,
                "length_ms": played,
            }
        )
        earliest = start + played + GAP_MS
    return plan


def build_voice_track(
    ffmpeg: str, plan: list[dict], wavs: dict[str, Path], video_s: float, out: Path
) -> None:
    """Mix all the clips into one track, each at its moment, over silence.

    Why a silent base track? Without it, the audio would only begin when the
    first clip begins, say 2 seconds in. MP4 files can say "audio starts at
    2 seconds", but some players ignore that and play the audio from 0, so the
    voice comes early and drifts out of sync with the captions. A silent track
    running the full length of the video makes the audio genuinely start at 0,
    so every player gets it right.

    'adelay' moves each clip to its start time. 'amix' layers them on the
    silence; normalize=0 stops amix from turning every clip down (by default it
    divides the volume by the number of inputs). 'duration=first' makes the
    result exactly as long as the silent base, which is as long as the video.
    """
    inputs = [
        "-f",
        "lavfi",
        "-t",
        f"{video_s:.3f}",
        "-i",
        f"anullsrc=r={SAMPLE_RATE}:cl=stereo",
    ]
    chains, labels = [], ["[0:a]"]
    for number, item in enumerate(plan, start=1):
        inputs += ["-i", str(wavs[item["id"]])]
        ms = item["start_ms"]
        chains.append(f"[{number}:a]adelay={ms}|{ms}[v{number}]")
        labels.append(f"[v{number}]")
    mix = (
        f"{''.join(labels)}amix=inputs={len(labels)}:duration=first:"
        "dropout_transition=0:normalize=0[out]"
    )
    graph = ";".join(chains + [mix])
    run(
        [ffmpeg, "-y", *inputs, "-filter_complex", graph, "-map", "[out]", str(out)],
        "mixing the voice track",
    )


# =============================================================================
# Step 3: exporting
# =============================================================================


def export_youtube(ffmpeg: str, video: Path, voice: Path, out: Path) -> None:
    """Full 1080p with the voice. The video was already encoded when cutting,
    so it's copied as it is (fast, no quality loss); only the audio is encoded."""
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video),
            "-i",
            str(voice),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out),
        ],
        "exporting the YouTube video",
    )


def export_github(
    ffmpeg: str,
    source: Path,
    out: Path,
    seconds: float,
    limit_mb: float,
    work_dir: Path,
) -> None:
    """A smaller copy that stays under GitHub's size limit.

    The size of a video is roughly bitrate x duration, so we work out the
    bitrate that fits, and use two-pass encoding, which hits a target size far
    more accurately than one pass. If the result is still too big, we lower the
    bitrate and try again.
    """
    limit_bytes = limit_mb * 1024 * 1024
    audio_kbps = 64
    total_kbps = limit_bytes * 8 / seconds / 1000 * 0.92  # keep room for the container
    video_kbps = max(int(total_kbps - audio_kbps), 120)
    log = str(work_dir / "github_pass")
    scale = "1280:-2"

    for attempt in range(1, 5):
        common = [
            "-vf",
            f"scale={scale},fps=24",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-b:v",
            f"{video_kbps}k",
            "-passlogfile",
            log,
        ]
        run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                *common,
                "-pass",
                "1",
                "-an",
                "-f",
                "null",
                os.devnull,
            ],
            "exporting the GitHub video (pass 1)",
        )
        run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(source),
                *common,
                "-pass",
                "2",
                "-c:a",
                "aac",
                "-b:a",
                f"{audio_kbps}k",
                "-ac",
                "1",
                "-movflags",
                "+faststart",
                str(out),
            ],
            "exporting the GitHub video (pass 2)",
        )
        size = out.stat().st_size
        if size <= limit_bytes:
            print(f"  GitHub video: {size / 1024 / 1024:.1f} MB at {video_kbps} kbps")
            break
        print(
            f"  Attempt {attempt}: {size / 1024 / 1024:.1f} MB is over the limit, retrying smaller..."
        )
        video_kbps = max(int(video_kbps * limit_bytes / size * 0.9), 80)
        if video_kbps <= 150:
            scale = "960:-2"  # at very low bitrates, a smaller picture looks better
    else:
        print(
            f"  ! Still over {limit_mb} MB: the video may be too long for GitHub's limit."
        )

    for leftover in work_dir.glob("github_pass*"):
        leftover.unlink(missing_ok=True)


def srt_time(ms: int) -> str:
    hours, rest = divmod(ms, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def write_srt(plan: list[dict], texts: dict[str, str], out: Path) -> None:
    """Subtitles: each scene's narration, shown while it's spoken."""
    lines = []
    for number, item in enumerate(plan, start=1):
        end = item["start_ms"] + item["length_ms"]
        lines += [
            str(number),
            f"{srt_time(item['start_ms'])} --> {srt_time(end)}",
            texts[item["id"]],
            "",
        ]
    out.write_text("\n".join(lines), encoding="utf-8")


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add narration and export the demo videos."
    )
    parser.add_argument("--scenes", default="demo/scenes.json", type=Path)
    parser.add_argument("--out", default="demo/output", type=Path)
    parser.add_argument(
        "--voice",
        default="en-US-AriaNeural",
        help="an edge-tts voice; list them with: edge-tts --list-voices",
    )
    parser.add_argument(
        "--rate", default="+0%", help='speaking speed, like "+10%%" or "-5%%"'
    )
    parser.add_argument("--max-speedup", default=DEFAULT_MAX_SPEEDUP, type=float)
    parser.add_argument("--github-limit-mb", default=GITHUB_LIMIT_MB, type=float)
    args = parser.parse_args()

    out_dir = args.out.resolve()
    work = out_dir / "work"
    work.mkdir(parents=True, exist_ok=True)

    timings = json.loads((out_dir / "timings.json").read_text(encoding="utf-8"))
    if timings.get("failed_scene"):
        print(
            f"! The recording stopped in scene '{timings['failed_scene']}': "
            "the video will only include the scenes before it."
        )
    scenes = json.loads(args.scenes.read_text(encoding="utf-8"))["scenes"]
    texts = {s["id"]: s["voice"].strip() for s in scenes if s.get("voice", "").strip()}
    captions = timings["captions"]
    cuts = sorted(timings["cuts"], key=lambda c: c["start_ms"])

    ffmpeg, ffprobe = find_ffmpeg()

    print("1/5 Cutting the long waits...")
    cut_mp4 = work / "cut.mp4"
    cut_video(ffmpeg, out_dir / "raw_recording.webm", cut_mp4, cuts)
    video_s = duration_s(ffprobe, cut_mp4)
    removed = sum(c["end_ms"] - c["start_ms"] for c in cuts) / 1000
    print(f"    removed {removed:.1f} s of waiting; the video is now {video_s:.1f} s")

    print(f"2/5 Generating the narration with {args.voice}...")
    recorded = [c for c in captions if c["id"] in texts]
    mp3s = {c["id"]: work / f"voice_{c['id']}.mp3" for c in recorded}
    asyncio.run(
        synthesize_all([(texts[i], p) for i, p in mp3s.items()], args.voice, args.rate)
    )
    clip_ms = {i: int(duration_s(ffprobe, p) * 1000) for i, p in mp3s.items()}

    print("3/5 Placing each clip at its caption...")
    plan = schedule(recorded, clip_ms, cuts, int(video_s * 1000), args.max_speedup)
    wavs = {}
    for item in plan:
        wavs[item["id"]] = work / f"voice_{item['id']}.wav"
        prepare_clip(ffmpeg, mp3s[item["id"]], wavs[item["id"]], item["tempo"])
        sped = f"  (sped up {item['tempo']:.2f}x)" if item["tempo"] > 1.001 else ""
        print(f"    {item['id']}: {item['start_ms'] / 1000:.1f} s{sped}")
    voice_wav = work / "voice_track.wav"
    build_voice_track(ffmpeg, plan, wavs, video_s, voice_wav)

    print("4/5 Exporting demo_youtube.mp4...")
    youtube = out_dir / "demo_youtube.mp4"
    export_youtube(ffmpeg, cut_mp4, voice_wav, youtube)

    print("5/5 Exporting demo_github.mp4 and subtitles.srt...")
    export_github(
        ffmpeg,
        youtube,
        out_dir / "demo_github.mp4",
        video_s,
        args.github_limit_mb,
        work,
    )
    write_srt(plan, texts, out_dir / "subtitles.srt")

    print(
        f"\nDone. In {out_dir}:\n  demo_youtube.mp4\n  demo_github.mp4\n  subtitles.srt"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
