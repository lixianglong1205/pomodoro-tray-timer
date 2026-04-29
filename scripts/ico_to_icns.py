from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

_ICONSET_SPECS: list[tuple[str, int]] = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Windows .ico file into a macOS .icns file (requires macOS 'iconutil').",
    )
    parser.add_argument("input_ico", type=Path, help="Path to input .ico")
    parser.add_argument("output_icns", type=Path, help="Path to output .icns")
    parser.add_argument(
        "--keep-iconset",
        action="store_true",
        help="Keep the intermediate *.iconset directory (useful for debugging).",
    )
    return parser.parse_args(argv)


def _best_ico_image(path: Path) -> Image.Image:
    """
    ICO files can contain multiple sizes. Prefer the largest available image.
    Pillow exposes them as frames; we pick the frame with the largest area.
    """
    img = Image.open(path)

    best = img
    best_area = img.size[0] * img.size[1]

    if getattr(img, "n_frames", 1) > 1:
        for i in range(img.n_frames):
            img.seek(i)
            area = img.size[0] * img.size[1]
            if area > best_area:
                best = img.copy()
                best_area = area

        # Reset for callers; best is a detached copy.
        img.seek(0)

    if best.mode != "RGBA":
        best = best.convert("RGBA")
    return best


def _ensure_iconutil() -> str:
    if platform.system() != "Darwin":
        raise RuntimeError("This script must be run on macOS (needs 'iconutil').")
    iconutil = shutil.which("iconutil")
    if iconutil is None:
        raise RuntimeError("Command not found: iconutil (expected on macOS).")
    return iconutil


def _write_iconset(source: Image.Image, iconset_dir: Path) -> None:
    iconset_dir.mkdir(parents=True, exist_ok=True)
    for filename, size in _ICONSET_SPECS:
        out_path = iconset_dir / filename
        resized = source.resize((size, size), resample=Image.Resampling.LANCZOS)
        resized.save(out_path, format="PNG")


def _convert_iconset_to_icns(iconutil: str, iconset_dir: Path, output_icns: Path) -> None:
    output_icns.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603
        [iconutil, "-c", "icns", str(iconset_dir), "-o", str(output_icns)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    iconutil = _ensure_iconutil()

    input_ico: Path = args.input_ico
    output_icns: Path = args.output_icns

    if input_ico.suffix.lower() != ".ico":
        raise ValueError(f"Input must be a .ico file, got: {input_ico}")
    if output_icns.suffix.lower() != ".icns":
        raise ValueError(f"Output must be a .icns file, got: {output_icns}")
    if not input_ico.exists():
        raise FileNotFoundError(input_ico)

    base = _best_ico_image(input_ico)

    iconset_dir = output_icns.with_suffix(".iconset")
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)

    try:
        _write_iconset(base, iconset_dir)
        _convert_iconset_to_icns(iconutil, iconset_dir, output_icns)
    finally:
        if not args.keep_iconset and iconset_dir.exists():
            shutil.rmtree(iconset_dir)

    if not output_icns.exists():
        raise RuntimeError("Conversion finished but output file is missing.")

    print(f"[OK] Wrote: {output_icns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

