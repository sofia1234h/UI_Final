#!/usr/bin/env python3
"""
Build All Skeletons - Config-driven orchestrator

Runs the full pipeline: video -> pose CSV -> skeleton JSON
for all configured clips.

Usage:
    python scripts/build_all.py              # Build all clips
    python scripts/build_all.py --force      # Re-extract even if CSV exists
    python scripts/build_all.py --only good_squat  # Single clip only
    python scripts/build_all.py --list       # List configured clips

Videos are expected in videos/ (gitignored).
CSVs go to data/pose_csvs/ (committed).
JSONs go to static/skeletons/ (committed).
"""

import argparse
import os
import sys
from pathlib import Path

# Add scripts dir to path for imports
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from extract_pose import find_dynalytix, extract_pose
from csv_to_skeleton import convert_csv_to_skeleton

# Project paths
PROJECT_ROOT = SCRIPTS_DIR.parent
VIDEOS_DIR = PROJECT_ROOT / "videos"
CSV_DIR = PROJECT_ROOT / "data" / "pose_csvs"
SKELETON_DIR = PROJECT_ROOT / "static" / "skeletons"


# ============================================================================
# CLIP CONFIGURATION
# Edit this dict to add/modify skeleton clips
# ============================================================================
CLIPS = {
    # output_name: {video, frames, mirror, label}
    "good_squat": {
        "video": "good_squat.mov",
        "frames": None,  # Full video, or "45:120" for range
        "mirror": False,
        "label": "Good Squat",
    },
    "heel_rise": {
        "video": "heel_rise.mov",
        "frames": None,
        "mirror": False,
        "label": "Heel Rise",
    },
    "forward_lean": {
        "video": "forward_lean.mov",
        "frames": None,
        "mirror": False,
        "label": "Forward Lean",
    },
    "lumbar_flexion": {
        "video": "lumbar_flexion.mov",
        "frames": None,
        "mirror": False,
        "label": "Lumbar Flexion",
    },
}
# ============================================================================


def parse_frame_range(frame_str: str | None) -> tuple[int, int | None] | None:
    """Parse frame range string to tuple."""
    if frame_str is None:
        return None
    parts = frame_str.split(":")
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if len(parts) > 1 and parts[1] else None
    return (start, end)


def build_clip(
    name: str,
    config: dict,
    dynalytix_path: Path | None,
    force: bool = False,
) -> tuple[bool, str, int]:
    """
    Build a single clip.

    Returns:
        (success, message, frame_count)
    """
    video_path = VIDEOS_DIR / config["video"]
    csv_path = CSV_DIR / f"{name}.csv"
    json_path = SKELETON_DIR / f"{name}.json"

    # Check if video exists
    if not video_path.exists():
        return (False, f"video not found ({config['video']})", 0)

    # Step 1: Extract CSV (if needed)
    if not csv_path.exists() or force:
        if dynalytix_path is None:
            return (False, "dynalytix not found for extraction", 0)

        print(f"  Extracting pose data from {video_path.name}...")
        success = extract_pose(video_path, csv_path, dynalytix_path)
        if not success:
            return (False, "extraction failed", 0)
        print(f"  -> {csv_path.name}")
    else:
        print(f"  Using existing CSV: {csv_path.name}")

    # Step 2: Convert to JSON
    print(f"  Converting to skeleton JSON...")
    try:
        frame_range = parse_frame_range(config.get("frames"))
        result = convert_csv_to_skeleton(
            input_path=csv_path,
            output_path=json_path,
            label=config.get("label", name),
            downsample=2,
            frame_range=frame_range,
            mirror=config.get("mirror", False),
        )
        frame_count = len(result["frames"])
        print(f"  -> {json_path.name}")
        return (True, "CSV + JSON written", frame_count)
    except SystemExit:
        # Orientation check failed
        return (False, "orientation check failed (inverted)", 0)
    except Exception as e:
        return (False, str(e), 0)


def main():
    parser = argparse.ArgumentParser(
        description="Build skeleton data from videos"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-extract CSV even if it exists"
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Build only this clip (e.g., --only good_squat)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List configured clips and exit"
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip extraction step, only convert existing CSVs to JSON"
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        print("Configured clips:")
        print("-" * 60)
        for name, config in CLIPS.items():
            video_path = VIDEOS_DIR / config["video"]
            csv_path = CSV_DIR / f"{name}.csv"
            json_path = SKELETON_DIR / f"{name}.json"

            status = []
            if video_path.exists():
                status.append("video \u2713")
            else:
                status.append("video \u2717")
            if csv_path.exists():
                status.append("csv \u2713")
            if json_path.exists():
                status.append("json \u2713")

            print(f"  {name}")
            print(f"    Video: {config['video']}")
            print(f"    Label: {config.get('label', name)}")
            print(f"    Status: {', '.join(status)}")
            print()
        return

    # Ensure directories exist
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    SKELETON_DIR.mkdir(parents=True, exist_ok=True)

    # Find dynalytix (only needed for extraction)
    dynalytix_path = None
    if not args.skip_extract:
        dynalytix_path = find_dynalytix()
        if dynalytix_path:
            print(f"Using dynalytix at: {dynalytix_path}")
        else:
            print("Warning: dynalytix not found - extraction will be skipped")
            print("  Set DYNALYTIX_PATH or clone dynalytix next to this repo")
        print()

    # Determine which clips to build
    if args.only:
        if args.only not in CLIPS:
            print(f"Error: Unknown clip '{args.only}'", file=sys.stderr)
            print(f"Available: {', '.join(CLIPS.keys())}", file=sys.stderr)
            sys.exit(1)
        clips_to_build = {args.only: CLIPS[args.only]}
    else:
        clips_to_build = CLIPS

    # Build each clip
    results = []
    for name, config in clips_to_build.items():
        print(f"\n{'=' * 60}")
        print(f"Building: {name}")
        print("=" * 60)

        success, message, frame_count = build_clip(
            name, config, dynalytix_path, force=args.force
        )
        results.append((name, success, message, frame_count))

    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for name, success, message, frame_count in results:
        if success:
            print(f"\u2713 {name:20} ({frame_count} frames, {message})")
        else:
            print(f"\u2717 {name:20} \u2014 {message}, skipped")

    # Exit with error if any failed
    if not all(r[1] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
