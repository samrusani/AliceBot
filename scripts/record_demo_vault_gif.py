#!/usr/bin/env python3
"""Record docs/examples/alice-memory-demo.gif from a real demo --vault run.

Runs ``alice-memory demo --vault docs/examples/demo-vault`` against a tmp
data-dir. Frames are that stdout. Pillow comes from the system Python.
ffmpeg is /opt/homebrew/bin/ffmpeg. Do not import this from CI.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
VAULT = REPO_ROOT / "docs" / "examples" / "demo-vault"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "examples" / "alice-memory-demo.gif"
DEFAULT_FFMPEG = Path("/opt/homebrew/bin/ffmpeg")
CANARY = "harbour-watch-29"
QUOTE_LABEL = "will quote"

BG = (13, 17, 23)
FG = (230, 237, 243)
PROMPT_FG = (126, 231, 135)
WIDTH = 920
PAD = 28
FONT_SIZE = 17
LINE_HEIGHT = 24
FPS = 12
HOLD_FRAMES = 36
CHARS_PER_FRAME = 3
LINE_HOLD = 3

FONT_CANDIDATES = (
    Path("/System/Library/Fonts/SFNSMono.ttf"),
    Path("/System/Library/Fonts/Menlo.ttc"),
    Path("/System/Library/Fonts/Monaco.ttf"),
    Path("/System/Library/Fonts/Supplemental/Courier New.ttf"),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record the committed demo-vault GIF from a real alice-memory run."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="GIF path. Default: docs/examples/alice-memory-demo.gif",
    )
    parser.add_argument(
        "--alice-memory",
        type=Path,
        default=None,
        help="alice-memory executable. Default: .venv/bin/alice-memory or PATH.",
    )
    parser.add_argument(
        "--ffmpeg",
        type=Path,
        default=DEFAULT_FFMPEG,
        help="ffmpeg executable.",
    )
    return parser


def _resolve_alice_memory(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    env = os.environ.get("ALICE_MEMORY_BIN")
    if env:
        return Path(env)
    venv_bin = REPO_ROOT / ".venv" / "bin" / "alice-memory"
    if venv_bin.is_file():
        return venv_bin
    found = shutil.which("alice-memory")
    if found:
        return Path(found)
    raise SystemExit("alice-memory not found. Pass --alice-memory.")


def _load_font():
    from PIL import ImageFont

    for path in FONT_CANDIDATES:
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_line(text: str, font, max_width: int) -> list[str]:
    if not text:
        return [""]
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if current == "" else f"{current} {word}"
        if font.getlength(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def _display_lines(command: str, stdout: str, font, max_width: int) -> list[tuple[str, tuple[int, int, int]]]:
    rows: list[tuple[str, tuple[int, int, int]]] = []
    for wrapped in _wrap_line(f"$ {command}", font, max_width):
        rows.append((wrapped, PROMPT_FG))
    rows.append(("", FG))
    for raw in stdout.splitlines():
        wrapped = _wrap_line(raw, font, max_width)
        for part in wrapped:
            rows.append((part, FG))
    return rows


def _render_frame(rows: list[tuple[str, tuple[int, int, int]]], font, height: int):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(image)
    y = PAD
    for text, color in rows:
        draw.text((PAD, y), text, font=font, fill=color)
        y += LINE_HEIGHT
    return image


def _typed_prefixes(text: str) -> list[str]:
    if text == "":
        return [""]
    prefixes = [text[: index] for index in range(CHARS_PER_FRAME, len(text), CHARS_PER_FRAME)]
    if not prefixes or prefixes[-1] != text:
        prefixes.append(text)
    return prefixes


def _build_frames(
    rows: list[tuple[str, tuple[int, int, int]]],
    font,
    height: int,
    frame_dir: Path,
) -> int:
    written = 0

    def save(current: list[tuple[str, tuple[int, int, int]]]) -> None:
        nonlocal written
        written += 1
        path = frame_dir / f"frame_{written:04d}.png"
        _render_frame(current, font, height).save(path)

    current: list[tuple[str, tuple[int, int, int]]] = []
    for index, (text, color) in enumerate(rows):
        if index == 0 or text.startswith("will quote"):
            for prefix in _typed_prefixes(text):
                save([*current, (prefix, color)])
            current.append((text, color))
            continue
        current.append((text, color))
        for _ in range(LINE_HOLD):
            save(current)
    for _ in range(HOLD_FRAMES):
        save(current)
    return written


def _run_demo(alice_memory: Path, data_dir: Path) -> str:
    env = os.environ.copy()
    env.pop("ALICE_AGENT_API_KEY", None)
    completed = subprocess.run(
        [
            str(alice_memory),
            "demo",
            "--vault",
            str(VAULT),
            "--data-dir",
            str(data_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"alice-memory demo failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    stdout = completed.stdout
    if QUOTE_LABEL not in stdout or CANARY not in stdout:
        raise SystemExit("demo stdout is missing will quote or the harbour-watch canary")
    return stdout


def _encode_gif(ffmpeg: Path, frame_dir: Path, frame_count: int, output: Path) -> None:
    if not ffmpeg.is_file():
        raise SystemExit(f"ffmpeg not found: {ffmpeg}")
    palette = frame_dir / "palette.png"
    pattern = str(frame_dir / "frame_%04d.png")
    subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-vf",
            "palettegen=max_colors=64:stats_mode=diff",
            str(palette),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            str(ffmpeg),
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-i",
            str(palette),
            "-lavfi",
            "paletteuse=dither=bayer:bayer_scale=5",
            "-frames:v",
            str(frame_count),
            str(output),
        ],
        check=True,
        capture_output=True,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Pillow is required on the system Python. Do not add it to pyproject.toml."
        ) from exc

    args = _build_parser().parse_args(argv)
    alice_memory = _resolve_alice_memory(args.alice_memory)
    if not VAULT.is_dir():
        raise SystemExit(f"missing demo vault: {VAULT}")

    home = Path.home()
    alice_existed = (home / ".alice").exists()
    data_dir = Path(tempfile.mkdtemp(prefix="am-demo-", dir="/tmp"))
    if data_dir.resolve() == (home / ".alice").resolve():
        raise SystemExit("refusing to write the live ~/.alice vault")

    try:
        stdout = _run_demo(alice_memory, data_dir)
        if not alice_existed and (home / ".alice").exists():
            raise SystemExit("demo wrote ~/.alice")
        command = (
            "alice-memory demo --vault docs/examples/demo-vault "
            f"--data-dir {data_dir}"
        )
        font = _load_font()
        max_width = WIDTH - (PAD * 2)
        rows = _display_lines(command, stdout.rstrip("\n"), font, max_width)
        height = PAD * 2 + LINE_HEIGHT * len(rows)
        with tempfile.TemporaryDirectory(prefix="am-demo-frames-") as frame_home:
            frame_dir = Path(frame_home)
            frame_count = _build_frames(rows, font, height, frame_dir)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            _encode_gif(args.ffmpeg, frame_dir, frame_count, args.output)
    finally:
        shutil.rmtree(data_dir, ignore_errors=True)

    header = args.output.read_bytes()[:6]
    if header not in {b"GIF87a", b"GIF89a"}:
        raise SystemExit(f"output is not a GIF: {args.output}")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
