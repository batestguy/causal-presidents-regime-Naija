"""Turn the captured stills into the demo: slow zoom, one caption pill per shot, two music beds, encode.

Same shape as the Tableau Nigeria MPI Equity Atlas demo (`docs/demo/`): 1600x1000 stills at 30 fps, a green
caption pill bottom-right, and a music bed. The difference is the bed: two records, each taken from 19 s and
run for 41 s, the second looped so the track keeps filling if the cut grows.

    python tools/build_demo.py                # writes docs/demo/demo.mp4
    python tools/build_demo.py --dry-run      # prints the shot list and the total length

Every duration and caption is declared here. Nothing is read from a take log, because these are stills: a
screenshot does not drift between runs the way a recording does.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs" / "demo"
MUSIC_A = ROOT / "Nobody Fails by Ofege- Listen on Audiomack.m4a"
MUSIC_B = ROOT / "I Am William by 2Shotz featuring M.I Abaga- Listen on Audiomack.m4a"
MUSIC_IN = 19.0          # seconds into each record, as requested
MUSIC_BLOCK = 41.0       # seconds of each record, as requested
W, H, FPS = 1600, 1000, 30
FONT = Path("C:/Windows/Fonts/segoeuib.ttf")
PILL = "0x1E7A4F"        # the site's accent, a shade darker so white text holds on it

# (file, seconds, caption). Order is the running order, and the durations sum to two 41-second music blocks.
SHOTS = [
    ("01_cover.png", 8.0, "Causal Presidents · Nigeria, 1999 to present"),
    ("02_study.png", 7.5, "Twelve outcomes. Pick what to study."),
    ("03_compare.png", 8.0, "What gets compared, assuming what."),
    ("04_graph.png", 8.0, "The assumption, drawn. The adjustment set computed from it."),
    ("05_estimates_refused.png", 8.5, "No number here, and the reason why."),
    ("06_estimates_number.png", 9.5, "+0.4678, an interval, and the check that failed."),
    ("07_chart.png", 8.0, "Breaks, and each tenure against the trend."),
    ("08_designs.png", 9.0, "99 countries. Four windows. None identified."),
    ("09_limits.png", 7.5, "What it does not claim."),
    ("10_ask.png", 8.0, "Ask a question: plain first, technical on demand."),
]


def ffmpeg_bin(name: str) -> str:
    found = shutil.which(name)
    if found and Path(found).exists():
        return found
    root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for package in sorted(root.glob("Gyan.FFmpeg*")):
        for exe in package.rglob(f"{name}.exe"):
            return str(exe)
    raise SystemExit(f"{name} not found; install it with: winget install Gyan.FFmpeg")


def escape_text(text: str) -> str:
    """drawtext reads its argument as filter syntax: colon, comma, apostrophe and % all need care."""
    return (text.replace("\\", r"\\\\").replace(":", r"\:")
                .replace(",", r"\,").replace("'", "’").replace("%", r"\%"))


def clip(index: int, still: Path, seconds: float, caption: str) -> Path:
    out = DEMO / "build" / f"clip{index:02d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * FPS)
    font = FONT.as_posix().replace(":", r"\:")
    # A 5 % push over the shot. Without it ten stills read as ten slides; with it the eye has something to
    # follow and the compression has no flat field to band on.
    vf = (
        f"zoompan=z='min(1+0.00035*on,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={W}x{H}:fps={FPS},"
        f"drawtext=fontfile='{font}':text='{escape_text(caption)}':fontsize=27:fontcolor=white"
        f":box=1:boxcolor={PILL}@0.95:boxborderw=18:x=w-tw-44:y=h-th-44"
    )
    cmd = [
        ffmpeg_bin("ffmpeg"), "-y", "-v", "error",
        "-loop", "1", "-i", str(still), "-t", f"{seconds}",
        "-vf", vf, "-r", str(FPS), "-pix_fmt", "yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"ffmpeg failed on {still.name}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total = sum(seconds for _, seconds, _ in SHOTS)
    print(f"{len(SHOTS)} shots, {total:.1f}s, {W}x{H} at {FPS} fps")
    if args.dry_run:
        for name, seconds, caption in SHOTS:
            print(f"  {name:<26} {seconds:>5.1f}s  {caption}")
        return 0

    if not MUSIC_A.exists():
        raise SystemExit(f"music not found: {MUSIC_A.name}")
    if not MUSIC_B.exists():
        raise SystemExit(f"music not found: {MUSIC_B.name}")

    clips = []
    for i, (name, seconds, caption) in enumerate(SHOTS, start=1):
        still = DEMO / name
        if not still.exists():
            raise SystemExit(f"missing still {still.relative_to(ROOT)} — capture at {W}x{H} first")
        print(f"  shot {i:02d}  {name:<26} {seconds:>5.1f}s  {caption}")
        clips.append(clip(i, still, seconds, caption))

    listing = DEMO / "build" / "clips.txt"
    listing.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")

    out = DEMO / "demo.mp4"
    # Two records, 41 seconds each, both entered at 19 s. The second is fed with -stream_loop so the cut can
    # grow past 82 s without the soundtrack running out; the trim to `second` is what actually ends it.
    second = max(0.0, total - MUSIC_BLOCK)
    fade_out = max(0.0, total - 3.0)
    audio = (
        f"[1:a]atrim=0:{MUSIC_BLOCK},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.5[a1];"
        f"[2:a]atrim=0:{second:.2f},asetpts=PTS-STARTPTS[a2];"
        f"[a1][a2]concat=n=2:v=0:a=1,afade=t=out:st={fade_out:.2f}:d=3[a]"
    )
    cmd = [
        ffmpeg_bin("ffmpeg"), "-y", "-v", "error",
        "-f", "concat", "-safe", "0", "-i", str(listing),
        "-ss", str(MUSIC_IN), "-t", str(MUSIC_BLOCK), "-i", str(MUSIC_A),
        "-stream_loop", "-1", "-ss", str(MUSIC_IN), "-i", str(MUSIC_B),
        "-filter_complex", audio,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-movflags", "+faststart", "-shortest", "-t", f"{total}",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("ffmpeg failed on the final mux")

    size = out.stat().st_size / 1e6
    print(f"\nwrote {out.relative_to(ROOT)} ({size:.1f} MB, {total:.1f}s)")
    print(f"poster: docs/demo/{SHOTS[0][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
