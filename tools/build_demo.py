"""Assemble the demo: trim the take, burn one caption per shot, lay the record underneath, encode.

Two sources are supported:

    python tools/build_demo.py --take desktop     # the recorded walk, the default
    python tools/build_demo.py --stills           # fall back to the 1600x1000 stills

`--take` reads the shot log `tools/record_demo.mjs` wrote and the `.webm` it recorded. Every caption window is
derived from that log: the window runs from the shot's cut to the next cut. Nothing is hard-coded, because a
take drifts by seconds between runs and a caption that lands late reads as a mistake.

The soundtrack is one record, entered at 19 s and faded at both ends, so the whole cut sits on a single track.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs" / "demo"
RAW = ROOT / "build" / "demo"
MUSIC = ROOT / "Nobody Fails by Ofege- Listen on Audiomack.m4a"
MUSIC_IN = 19.0
FONT = Path("C:/Windows/Fonts/segoeuib.ttf")
PILL = "0x1E7A4F"

# One caption per recorded shot. Keyed by the label prefix the recorder writes, so a renamed shot fails here
# rather than silently losing its line. `None` leaves the stretch uncaptioned instead of inheriting the
# previous caption.
CAPTIONS = {
    "home": "Nigeria, 1999 to present. Thirty-six model cards.",
    "home scrolled": "The premise: what can and cannot be compared.",
    "home about": "About the study, and the photographs' credits.",
    "study": "Two outcomes, ticked. Every card states its coverage.",
    "study chosen": "Two outcomes chosen. Next opens the comparison.",
    "study one": "One outcome: the card that carries a published figure.",
    "compare": "What gets compared, and the assumption it rests on.",
    "compare scrolled": "One sentence per outcome. No number yet.",
    "graph": "The assumption, drawn.",
    "graph adjustment": "The adjustment set, computed from the graph by dagitty.",
    "estimate refused": "No number, and the reason. Below it, the trend.",
    "technical": "The technical version: sample, verdict, the failed check.",
    "estimate second": "A second outcome, the same shape.",
    "estimate published": "+0.4678: what is associated with what, in words.",
    "published technical": "The p-value, the standard error, the formula.",
    "chart": "The series, drawn against the tenures.",
    "chart breaks": "Where the series changes, from the changepoint search.",
    "chart grouping": "The other grouping: no state-level series here.",
    "chart tenure": "Each tenure against a trend that never saw who was in power.",
    "designs top": "The published numbers, and what decided each verdict.",
    "designs grid": "129 specifications: the support, and the sign flips.",
    "designs synthetic": "99 countries. Four windows. None identified.",
    "designs transitions": "What moved at a transition, by month.",
    "methodology": "What it does not claim.",
    "ask": "Ask the corpus a question.",
    "ask one": "How many cards carry a published number?",
    "ask two": "Why can't the site compare PDP and APC tenures?",
    "ask three": "How much of the series is observed, not interpolated?",
    "ask technical": "The technical section, one click away.",
    "end card": None,
}

# Stills fallback: (file, seconds, caption). Kept because the stills are what the README shows.
STILLS = [
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
    return (text.replace("\\", r"\\\\").replace(":", r"\:")
                .replace(",", r"\,").replace("'", "’").replace("%", r"\%"))


def probe(path: Path) -> tuple[float, int, int]:
    out = subprocess.run(
        [ffmpeg_bin("ffprobe"), "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    stream = data["streams"][0]
    return float(data["format"]["duration"]), int(stream["width"]), int(stream["height"])


def caption_chain(captions, font_size: int, margin: int) -> str:
    font = FONT.as_posix().replace(":", r"\:")
    chain = []
    for start, end, text in captions:
        enable = f"between(t,{start:.2f},{end:.2f})"
        chain.append(
            f"drawtext=fontfile='{font}':text='{escape_text(text)}':fontsize={font_size}:fontcolor=white"
            f":box=1:boxcolor={PILL}@0.95:boxborderw=18:x=w-tw-44:y=h-th-44:enable='{enable}'"
        )
    return ",".join(chain)


def mux(video: Path, duration: float, trim: float, captions, size: tuple[int, int], out: Path,
        font_size: int) -> None:
    fade_out = max(0.0, duration - 3.0)
    vf = caption_chain(captions, font_size, 44)
    cmd = [
        ffmpeg_bin("ffmpeg"), "-y", "-v", "error",
        "-ss", f"{trim}", "-i", str(video),
        "-ss", str(MUSIC_IN), "-i", str(MUSIC),
        "-filter_complex", f"[0:v]{vf}[v];[1:a]afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out:.2f}:d=3[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-movflags", "+faststart", "-t", f"{duration:.2f}",
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("ffmpeg failed on the final mux")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1e6:.1f} MB, {duration:.1f}s, "
          f"{size[0]}x{size[1]})")


def build_take(take: str) -> int:
    raw_dir = RAW / f"raw-{take}"
    takes = sorted(raw_dir.glob("*.webm"))
    if not takes:
        raise SystemExit(f"no capture in {raw_dir}; run: node tools/record_demo.mjs {take}")
    raw = takes[0]
    marks = json.loads((RAW / f"shots-{take}.json").read_text(encoding="utf-8"))

    total, width, height = probe(raw)
    trim = float(marks[0]["at"])
    duration = round(total - trim, 2)
    print(f"{take}: raw {total:.2f}s, trim {trim:.2f}s -> {duration:.2f}s at {width}x{height}")

    captions = []
    for i, mark in enumerate(marks):
        # Longest matching key, not first: "study chosen" must not inherit "study"'s line.
        key = max((k for k in CAPTIONS if mark["label"].startswith(k)), key=len, default=None)
        if key is None:
            raise SystemExit(f"no caption written for shot {mark['label']!r}")
        text = CAPTIONS[key]
        start = max(0.0, mark["at"] - trim)
        end = (marks[i + 1]["at"] - trim) if i + 1 < len(marks) else duration
        # An ask caption ends when the next question starts being typed, not when its answer lands: the
        # question box otherwise changes a second before the caption does, which reads as a mistake.
        if mark["label"].startswith("ask ") and i + 1 < len(marks):
            end = max(start + 0.5, end - 1.3)
        if text is None:
            print(f"  (no caption) {start:6.2f}-{min(end, duration):6.2f}  {mark['label']}")
            continue
        captions.append((start, min(end, duration), text))
        print(f"  caption {start:6.2f}-{min(end, duration):6.2f}  {text}")

    mux(raw, duration, trim, captions, (width, height), DEMO / "demo.mp4", font_size=28)
    return 0


def build_stills() -> int:
    clips = []
    work = DEMO / "build"
    work.mkdir(parents=True, exist_ok=True)
    for i, (name, seconds, caption) in enumerate(STILLS, start=1):
        still = DEMO / name
        if not still.exists():
            raise SystemExit(f"missing still {still.relative_to(ROOT)}")
        out = work / f"clip{i:02d}.mp4"
        font = FONT.as_posix().replace(":", r"\:")
        vf = (f"drawtext=fontfile='{font}'"
              f":text='{escape_text(caption)}':fontsize=27:fontcolor=white"
              f":box=1:boxcolor={PILL}@0.95:boxborderw=18:x=w-tw-44:y=h-th-44")
        cmd = [ffmpeg_bin("ffmpeg"), "-y", "-v", "error", "-loop", "1", "-i", str(still),
               "-t", f"{seconds}", "-vf", vf, "-r", "30", "-pix_fmt", "yuv420p",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(out)]
        subprocess.run(cmd, check=True, capture_output=True)
        clips.append(out)
    listing = work / "clips.txt"
    listing.write_text("".join(f"file '{c.as_posix()}'\n" for c in clips), encoding="utf-8")
    total = sum(s for _, s, _ in STILLS)
    mux_concat(listing, total)
    return 0


def mux_concat(listing: Path, total: float) -> None:
    fade_out = max(0.0, total - 3.0)
    cmd = [ffmpeg_bin("ffmpeg"), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
           "-ss", str(MUSIC_IN), "-i", str(MUSIC),
           "-filter_complex", f"[1:a]afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out:.2f}:d=3[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "24",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
           "-movflags", "+faststart", "-shortest", "-t", f"{total}", str(DEMO / "demo.mp4")]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"wrote docs/demo/demo.mp4 ({total:.1f}s)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--take", default="desktop")
    parser.add_argument("--stills", action="store_true", help="build from the stills instead of a recording")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not MUSIC.exists():
        raise SystemExit(f"music not found: {MUSIC.name}")

    if args.dry_run:
        marks = RAW / f"shots-{args.take}.json"
        if marks.exists():
            data = json.loads(marks.read_text(encoding="utf-8"))
            print(f"{len(data)} shots, {data[-1]['at'] - data[0]['at']:.1f}s")
            for mark in data:
                key = next((k for k in CAPTIONS if mark["label"].startswith(k)), None)
                print(f"  {mark['at']:7.2f}s  {mark['label']:<22} {CAPTIONS.get(key)}")
        else:
            print("no shot log yet; run tools/record_demo.mjs first")
        return 0

    return build_stills() if args.stills else build_take(args.take)


if __name__ == "__main__":
    raise SystemExit(main())
