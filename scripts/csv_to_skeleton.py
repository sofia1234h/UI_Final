#!/usr/bin/env python3
"""
CSV to Skeleton JSON Converter

Converts MediaPipe pose CSV files into JSON format suitable for skeleton_player.js.
Uses scripts/visualizer.py as the single source of truth for skeleton definitions.

Usage:
    python scripts/csv_to_skeleton.py data/pose_csvs/good_squat.csv static/skeletons/good_squat.json \\
        [--downsample 2] [--frames 45:120] [--label "Good Squat"] [--mirror]
"""

import argparse
import json
import sys
from pathlib import Path

# Import from the visualizer module (single source of truth)
from visualizer import (
    load_pose_csv,
    get_landmark_position,
    get_landmark_visibility,
    ALL_LANDMARK_NAMES,
    ALL_ANGLE_NAMES,
)


# Visibility threshold for considering a landmark "valid"
VISIBILITY_THRESHOLD = 0.5

# Padding for bounding box (5%)
PADDING = 0.05

# Key joints that must be visible for a frame to be valid
KEY_JOINTS = ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]


def parse_frame_range(frame_str: str) -> tuple[int, int | None]:
    """Parse a frame range string like '45:120' into (start, end)."""
    if ":" not in frame_str:
        raise ValueError(f"Invalid frame range: {frame_str}. Expected format: START:END")
    parts = frame_str.split(":")
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if parts[1] else None
    return start, end


def frame_is_valid(landmarks: dict) -> bool:
    """Check if a frame has enough visible key joints."""
    def side_valid(side: str) -> bool:
        return all(
            get_landmark_visibility(landmarks, f"{side}_{j}") >= VISIBILITY_THRESHOLD
            for j in ["hip", "knee", "ankle"]
        )
    return side_valid("left") or side_valid("right")


def compute_bounds(frames: list[dict]) -> tuple[float, float, float, float]:
    """Compute bounding box across all frames with padding."""
    all_x = []
    all_y = []

    for frame in frames:
        for name, pos in frame["joints"].items():
            if pos is not None:
                all_x.append(pos[0])
                all_y.append(pos[1])

    if not all_x or not all_y:
        return 0, 0, 1, 1

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    # Add padding
    width = max_x - min_x
    height = max_y - min_y
    pad_x = width * PADDING
    pad_y = height * PADDING

    return min_x - pad_x, min_y - pad_y, max_x + pad_x, max_y + pad_y


def normalize_frames(frames: list[dict], mirror: bool = False) -> tuple[list[dict], dict]:
    """
    Normalize all frames to 0-1 coordinates.

    MediaPipe pixel y goes DOWN, SVG y also goes DOWN, so NO flip needed.
    """
    min_x, min_y, max_x, max_y = compute_bounds(frames)
    width = max_x - min_x
    height = max_y - min_y

    if width == 0:
        width = 1
    if height == 0:
        height = 1

    normalized = []
    for frame in frames:
        new_joints = {}
        for name, pos in frame["joints"].items():
            if pos is None:
                new_joints[name] = None
            else:
                nx = (pos[0] - min_x) / width
                ny = (pos[1] - min_y) / height
                # NO flip: MediaPipe y and SVG y both go down
                if mirror:
                    nx = 1 - nx
                new_joints[name] = [round(nx, 4), round(ny, 4)]

        normalized.append({
            "t": frame["t"],
            "joints": new_joints,
            "angles": frame["angles"],
        })

    # If mirrored, swap left/right labels
    if mirror:
        for frame in normalized:
            # Swap joint names
            new_joints = {}
            for name, pos in frame["joints"].items():
                if name.startswith("left_"):
                    new_name = name.replace("left_", "right_")
                elif name.startswith("right_"):
                    new_name = name.replace("right_", "left_")
                else:
                    new_name = name
                new_joints[new_name] = pos
            frame["joints"] = new_joints

            # Swap angle names
            new_angles = {}
            for name, val in frame["angles"].items():
                if name.startswith("left_"):
                    new_name = name.replace("left_", "right_")
                elif name.startswith("right_"):
                    new_name = name.replace("right_", "left_")
                else:
                    new_name = name
                new_angles[new_name] = val
            frame["angles"] = new_angles

    bounds = {"w": 1.0, "h": 1.0}  # Normalized
    return normalized, bounds


def print_orientation_check(frames: list[dict]) -> bool:
    """
    Print orientation sanity check and return True if correct.

    Expects: nose.y < shoulders.y < hips.y < knees.y < ankles.y
    (smaller y = higher on screen, which is correct for head at top)
    """
    if not frames:
        print("No frames to check orientation")
        return False

    # Use middle frame
    mid_idx = len(frames) // 2
    frame = frames[mid_idx]
    joints = frame["joints"]

    def get_y(name: str) -> float | None:
        pos = joints.get(name)
        if pos is None:
            # Try the other side
            if name.startswith("left_"):
                pos = joints.get(name.replace("left_", "right_"))
            elif name.startswith("right_"):
                pos = joints.get(name.replace("right_", "left_"))
        return pos[1] if pos else None

    nose_y = get_y("nose")
    shoulder_y = get_y("left_shoulder")
    hip_y = get_y("left_hip")
    knee_y = get_y("left_knee")
    ankle_y = get_y("left_ankle")

    print("\nOrientation check (middle frame):")
    print(f"  nose          y={nose_y:.2f}   (expect: small, near top)" if nose_y else "  nose          [missing]")
    print(f"  shoulders     y={shoulder_y:.2f}" if shoulder_y else "  shoulders     [missing]")
    print(f"  hips          y={hip_y:.2f}" if hip_y else "  hips          [missing]")
    print(f"  knees         y={knee_y:.2f}" if knee_y else "  knees         [missing]")
    print(f"  ankles        y={ankle_y:.2f}   (expect: large, near bottom)" if ankle_y else "  ankles        [missing]")

    # Check orientation: nose should have smaller y than ankles
    if nose_y is not None and ankle_y is not None:
        if nose_y < ankle_y:
            print("\nResult: \u2713 correct")
            return True
        else:
            print("\nResult: \u2717 INVERTED \u2014 output skeleton will render upside-down")
            return False
    else:
        print("\nResult: [unable to verify - missing key landmarks]")
        return True  # Don't fail if we can't check


def convert_csv_to_skeleton(
    input_path: Path,
    output_path: Path,
    label: str = None,
    downsample: int = 2,
    frame_range: tuple[int, int | None] = None,
    mirror: bool = False,
) -> dict:
    """Convert a CSV file to skeleton JSON."""

    # Load CSV using visualizer module
    raw_data = load_pose_csv(input_path)

    if not raw_data:
        raise ValueError(f"No data found in CSV: {input_path}")

    # Apply frame range filter
    if frame_range:
        start, end = frame_range
        if end is None:
            end = len(raw_data)
        raw_data = raw_data[start:end]

    # Extract frames with valid joints
    raw_frames = []
    for idx, frame_data in enumerate(raw_data):
        landmarks = frame_data['landmarks']

        if not frame_is_valid(landmarks):
            continue

        # Convert landmarks to joints dict
        joints = {}
        for lm_name in ALL_LANDMARK_NAMES:
            pos = get_landmark_position(landmarks, lm_name)
            vis = get_landmark_visibility(landmarks, lm_name)
            if pos is not None and vis >= VISIBILITY_THRESHOLD:
                joints[lm_name] = list(pos)
            else:
                joints[lm_name] = None

        # Extract angles
        angles = {}
        for angle_name in ALL_ANGLE_NAMES:
            if angle_name in frame_data['angles']:
                angles[angle_name] = round(frame_data['angles'][angle_name], 1)

        raw_frames.append({
            "t": idx,
            "joints": joints,
            "angles": angles,
        })

    if not raw_frames:
        raise ValueError("No valid frames found in CSV")

    # Downsample
    if downsample > 1:
        raw_frames = raw_frames[::downsample]

    # Re-index time
    for i, frame in enumerate(raw_frames):
        frame["t"] = i

    # Normalize coordinates
    frames, bounds = normalize_frames(raw_frames, mirror=mirror)

    # Orientation sanity check
    if not print_orientation_check(frames):
        print("\nERROR: Skeleton appears inverted. Not writing output.", file=sys.stderr)
        sys.exit(1)

    # Calculate FPS (original is ~30fps, after downsample)
    original_fps = 30
    fps = original_fps / downsample

    # Build output
    result = {
        "label": label or input_path.stem,
        "fps": fps,
        "source_csv": input_path.name,
        "frame_range": list(frame_range) if frame_range else None,
        "bounds": bounds,
        "frames": frames,
    }

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert MediaPipe pose CSV to skeleton JSON"
    )
    parser.add_argument("input", type=Path, help="Input CSV file")
    parser.add_argument("output", type=Path, help="Output JSON file")
    parser.add_argument(
        "--downsample", type=int, default=2,
        help="Keep every Nth frame (default: 2)"
    )
    parser.add_argument(
        "--frames", type=str, default=None,
        help="Frame range as START:END (e.g., 45:120)"
    )
    parser.add_argument(
        "--label", type=str, default=None,
        help="Label for the skeleton"
    )
    parser.add_argument(
        "--mirror", action="store_true",
        help="Mirror skeleton horizontally"
    )

    args = parser.parse_args()

    frame_range = None
    if args.frames:
        frame_range = parse_frame_range(args.frames)

    try:
        result = convert_csv_to_skeleton(
            input_path=args.input,
            output_path=args.output,
            label=args.label,
            downsample=args.downsample,
            frame_range=frame_range,
            mirror=args.mirror,
        )
        print(f"\nConverted {len(result['frames'])} frames to {args.output}")
        print(f"  Label: {result['label']}")
        print(f"  FPS: {result['fps']}")
        if result['frame_range']:
            print(f"  Frame range: {result['frame_range'][0]}:{result['frame_range'][1]}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
