#!/usr/bin/env python3
"""
CSV to Skeleton JSON Converter

Converts MediaPipe pose CSV files from the dynalytix repo into
JSON format suitable for the skeleton player.

Usage:
    python csv_to_skeleton.py <input.csv> <output.json> [options]

Options:
    --downsample N    Keep every Nth frame (default: 2)
    --frames START:END  Trim to frame range (e.g., 45:120)
    --label NAME      Label for the skeleton (default: filename)
    --mirror          Flip x coordinates (face opposite direction)
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


# Landmarks we extract (in order)
LANDMARKS = [
    "nose",
    "left_shoulder", "right_shoulder",
    "left_elbow", "right_elbow",
    "left_wrist", "right_wrist",
    "left_hip", "right_hip",
    "left_knee", "right_knee",
    "left_ankle", "right_ankle",
    "left_heel", "right_heel",
]

# Angle columns to extract
ANGLE_COLUMNS = [
    "angle_left_elbow", "angle_right_elbow",
    "angle_left_shoulder", "angle_right_shoulder",
    "angle_left_hip", "angle_right_hip",
    "angle_left_knee", "angle_right_knee",
    "angle_left_ankle", "angle_right_ankle",
    "angle_upper_back", "angle_lower_back",
]

# Key joints that must be visible for a frame to be valid
KEY_JOINTS = ["left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle"]

VISIBILITY_THRESHOLD = 0.5
PADDING = 0.05  # 5% padding for bounding box


def parse_frame_range(frame_str: str) -> tuple[int, int]:
    """Parse a frame range string like '45:120' into (start, end)."""
    if ":" not in frame_str:
        raise ValueError(f"Invalid frame range: {frame_str}. Expected format: START:END")
    parts = frame_str.split(":")
    start = int(parts[0]) if parts[0] else 0
    end = int(parts[1]) if parts[1] else None
    return start, end


def extract_landmarks(row: pd.Series) -> dict:
    """Extract landmark positions from a CSV row."""
    joints = {}
    for lm in LANDMARKS:
        x = row.get(f"landmark_{lm}_x")
        y = row.get(f"landmark_{lm}_y")
        vis = row.get(f"landmark_{lm}_visibility", 0)

        if pd.isna(x) or pd.isna(y) or vis < VISIBILITY_THRESHOLD:
            joints[lm] = None
        else:
            joints[lm] = [float(x), float(y)]
    return joints


def extract_angles(row: pd.Series) -> dict:
    """Extract angle measurements from a CSV row."""
    angles = {}
    for col in ANGLE_COLUMNS:
        val = row.get(col)
        if pd.notna(val):
            # Remove 'angle_' prefix for cleaner output
            key = col.replace("angle_", "")
            angles[key] = round(float(val), 1)
    return angles


def frame_is_valid(joints: dict) -> bool:
    """Check if a frame has enough visible key joints."""
    # Need at least one side of hip/knee/ankle to be valid
    left_valid = all(joints.get(f"left_{j}") is not None for j in ["hip", "knee", "ankle"])
    right_valid = all(joints.get(f"right_{j}") is not None for j in ["hip", "knee", "ankle"])
    return left_valid or right_valid


def compute_bounds(frames: list[dict]) -> tuple[float, float, float, float]:
    """Compute bounding box across all frames with padding."""
    all_x = []
    all_y = []

    for frame in frames:
        for pos in frame["joints"].values():
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
    """Normalize all frames to 0-1 coordinates and flip y for SVG."""
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
                # Flip y so SVG renders right-side up (y=0 at top in SVG)
                ny = 1 - ny
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


def convert_csv_to_skeleton(
    input_path: Path,
    output_path: Path,
    label: str = None,
    downsample: int = 2,
    frame_range: tuple[int, int] = None,
    mirror: bool = False,
) -> dict:
    """Convert a CSV file to skeleton JSON."""

    # Read CSV
    df = pd.read_csv(input_path)

    # Apply frame range filter
    if frame_range:
        start, end = frame_range
        if end is None:
            end = len(df)
        df = df.iloc[start:end].reset_index(drop=True)

    # Extract frames
    raw_frames = []
    for idx, row in df.iterrows():
        joints = extract_landmarks(row)
        angles = extract_angles(row)

        if frame_is_valid(joints):
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
        print(f"Converted {len(result['frames'])} frames to {args.output}")
        print(f"  Label: {result['label']}")
        print(f"  FPS: {result['fps']}")
        if result['frame_range']:
            print(f"  Frame range: {result['frame_range'][0]}:{result['frame_range'][1]}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
