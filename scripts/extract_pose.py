#!/usr/bin/env python3
"""
Video to Pose CSV Extractor

Extracts MediaPipe pose data from a video file by invoking the dynalytix pipeline.
Requires the dynalytix repo to be cloned locally.

Usage:
    python scripts/extract_pose.py videos/good_squat.mov --output data/pose_csvs/good_squat.csv

Environment:
    DYNALYTIX_PATH - Path to dynalytix repo (default: ../dynalytix)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Default path to dynalytix repo (relative to this repo's parent)
DYNALYTIX_PATH = os.environ.get("DYNALYTIX_PATH", str(Path(__file__).parent.parent.parent / "dynalytix"))


def find_dynalytix() -> Path | None:
    """Find the dynalytix repo."""
    path = Path(DYNALYTIX_PATH)
    if path.exists() and (path / "main.py").exists():
        return path

    # Try some common locations
    alternatives = [
        Path.home() / "dynalytix",
        Path.home() / "projects" / "dynalytix",
        Path(__file__).parent.parent.parent / "dynalytix",
    ]

    for alt in alternatives:
        if alt.exists() and (alt / "main.py").exists():
            return alt

    return None


def extract_pose(video_path: Path, output_path: Path, dynalytix_path: Path) -> bool:
    """
    Extract pose data from video using dynalytix.

    Args:
        video_path: Path to input video file
        output_path: Path to output CSV file
        dynalytix_path: Path to dynalytix repo

    Returns:
        True if successful, False otherwise
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build command
    main_py = dynalytix_path / "main.py"
    cmd = [
        sys.executable,
        str(main_py),
        str(video_path),
        "--landmarks",
        "--output", str(output_path),
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(dynalytix_path),
            capture_output=False,  # Let output stream to terminal
            text=True,
        )
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error running dynalytix: {e}", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"Error: Could not find Python or dynalytix main.py", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Extract pose data from video using dynalytix"
    )
    parser.add_argument(
        "video",
        type=Path,
        help="Input video file (e.g., videos/good_squat.mov)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output CSV file (e.g., data/pose_csvs/good_squat.csv)"
    )
    parser.add_argument(
        "--dynalytix",
        type=Path,
        default=None,
        help=f"Path to dynalytix repo (default: $DYNALYTIX_PATH or {DYNALYTIX_PATH})"
    )

    args = parser.parse_args()

    # Check video exists
    if not args.video.exists():
        print(f"Error: Video file not found: {args.video}", file=sys.stderr)
        sys.exit(1)

    # Find dynalytix
    dynalytix_path = args.dynalytix
    if dynalytix_path is None:
        dynalytix_path = find_dynalytix()

    if dynalytix_path is None:
        print("Error: Could not find dynalytix repo.", file=sys.stderr)
        print(file=sys.stderr)
        print("To fix this, either:", file=sys.stderr)
        print(f"  1. Set DYNALYTIX_PATH environment variable:", file=sys.stderr)
        print(f"     export DYNALYTIX_PATH=/path/to/dynalytix", file=sys.stderr)
        print(file=sys.stderr)
        print(f"  2. Clone dynalytix next to this repo:", file=sys.stderr)
        print(f"     git clone --branch fms-demo https://github.com/Jolieabadir/dynalytix.git ../dynalytix", file=sys.stderr)
        print(file=sys.stderr)
        print(f"  3. Use --dynalytix flag:", file=sys.stderr)
        print(f"     python scripts/extract_pose.py video.mov -o output.csv --dynalytix /path/to/dynalytix", file=sys.stderr)
        sys.exit(1)

    print(f"Using dynalytix at: {dynalytix_path}")
    print(f"Input video: {args.video}")
    print(f"Output CSV: {args.output}")
    print()

    # Run extraction
    success = extract_pose(args.video, args.output, dynalytix_path)

    if success:
        print()
        print(f"\u2713 Successfully extracted pose data to {args.output}")
        sys.exit(0)
    else:
        print()
        print(f"\u2717 Failed to extract pose data", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
