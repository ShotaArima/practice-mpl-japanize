from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path


FONT_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
)
LICENSE_URL = (
    "https://raw.githubusercontent.com/google/fonts/main/"
    "ofl/notosansjp/OFL.txt"
)


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        print(f"exists: {destination}")
        return

    print(f"download: {url}")
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())
    print(f"saved: {destination}")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory that will contain .fonts, .fontconfig, and matplotlibrc.",
    )
    args = parser.parse_args()

    target_dir = args.target_dir.resolve()
    font_dir = target_dir / ".fonts"
    fontconfig_file = target_dir / ".fontconfig" / "fonts.conf"
    matplotlibrc = target_dir / "matplotlibrc"

    font_path = font_dir / "NotoSansJP[wght].ttf"
    license_path = font_dir / "OFL.txt"

    download(FONT_URL, font_path)
    download(LICENSE_URL, license_path)

    write_text(
        fontconfig_file,
        textwrap.dedent(
            f"""\
            <?xml version="1.0"?>
            <!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
            <fontconfig>
              <dir>{font_dir}</dir>
            </fontconfig>
            """
        ),
    )

    write_text(
        matplotlibrc,
        textwrap.dedent(
            """\
            font.family: Noto Sans JP
            axes.unicode_minus: False
            """
        ),
    )

    fc_cache = shutil.which("fc-cache")
    if fc_cache:
        subprocess.run([fc_cache, "-f", "-v", str(font_dir)], check=False)
    else:
        print("skip: fc-cache was not found")

    print()
    print("Use this environment variable before starting the kernel:")
    print(f"FONTCONFIG_FILE={fontconfig_file}")
    print()
    print("If matplotlib was already imported, restart the Jupyter kernel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
