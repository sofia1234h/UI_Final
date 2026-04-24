"""
Skeleton data definitions and CSV loading utilities.

Trimmed from dynalytix/visualizer_live.py - keeps only the data structures
and CSV parsing logic, no cv2 or visualization code.

This module is the single source of truth for what a "skeleton" means in
this app. Both csv_to_skeleton.py and other scripts import from here.

Source: https://github.com/Jolieabadir/dynalytix/blob/fms-demo/visualizer_live.py
"""

import csv
from pathlib import Path
from typing import Union

# Skeleton connections (landmark pairs to draw lines between)
# This matches the dynalytix visualizer_live.py SKELETON_CONNECTIONS
SKELETON_CONNECTIONS: list[tuple[str, str]] = [
    # Torso
    ('left_shoulder', 'right_shoulder'),
    ('left_shoulder', 'left_hip'),
    ('right_shoulder', 'right_hip'),
    ('left_hip', 'right_hip'),
    # Left arm
    ('left_shoulder', 'left_elbow'),
    ('left_elbow', 'left_wrist'),
    # Right arm
    ('right_shoulder', 'right_elbow'),
    ('right_elbow', 'right_wrist'),
    # Left leg
    ('left_hip', 'left_knee'),
    ('left_knee', 'left_ankle'),
    ('left_ankle', 'left_heel'),
    # Right leg
    ('right_hip', 'right_knee'),
    ('right_knee', 'right_ankle'),
    ('right_ankle', 'right_heel'),
]

# Angles displayed in the visualizer
DISPLAY_ANGLES: list[str] = [
    'left_elbow',
    'right_elbow',
    'left_knee',
    'right_knee',
    'left_shoulder',
    'right_shoulder',
]

# All angle columns that can appear in CSVs (superset of DISPLAY_ANGLES)
ALL_ANGLE_NAMES: list[str] = [
    'left_elbow',
    'right_elbow',
    'left_shoulder',
    'right_shoulder',
    'left_hip',
    'right_hip',
    'left_knee',
    'right_knee',
    'left_ankle',
    'right_ankle',
    'upper_back',
    'lower_back',
]

# Derive all landmark names from skeleton connections + nose
def _extract_landmark_names() -> list[str]:
    """Extract unique landmark names from SKELETON_CONNECTIONS."""
    names = set()
    for a, b in SKELETON_CONNECTIONS:
        names.add(a)
        names.add(b)
    # Add nose (commonly tracked but not in skeleton connections)
    names.add('nose')
    # Return in a consistent order
    return sorted(names)

ALL_LANDMARK_NAMES: list[str] = _extract_landmark_names()


def load_pose_csv(path: Union[str, Path]) -> list[dict]:
    """
    Load pose data from a MediaPipe CSV file.

    Args:
        path: Path to the CSV file with frame data

    Returns:
        List of frame dicts, each containing:
            - frame_number: int
            - timestamp_ms: float (if available)
            - landmarks: dict[str, dict] with 'x', 'y', 'visibility' for each landmark
            - angles: dict[str, float] with angle values in degrees

    CSV format expected:
        - frame_number column
        - timestamp_ms column (optional)
        - landmark_{name}_x, landmark_{name}_y, landmark_{name}_visibility columns
        - angle_{name} columns
    """
    path = Path(path)
    frames = []

    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Find all landmark columns
        landmark_cols = [col for col in fieldnames if col.startswith('landmark_')]

        for row in reader:
            frame_number = int(row.get('frame_number', 0))
            timestamp_ms = None
            if 'timestamp_ms' in row and row['timestamp_ms']:
                try:
                    timestamp_ms = float(row['timestamp_ms'])
                except (ValueError, TypeError):
                    pass

            # Extract landmarks
            landmarks = {}
            for col in landmark_cols:
                if col.endswith('_visibility'):
                    continue

                # Parse landmark name from column (e.g., 'landmark_left_shoulder_x')
                parts = col.split('_')
                landmark_name = '_'.join(parts[1:-1])  # Remove 'landmark' prefix and axis suffix
                axis = parts[-1]  # 'x', 'y', or 'z'

                if landmark_name not in landmarks:
                    landmarks[landmark_name] = {}

                value = row.get(col, '')
                if value and value != '':
                    try:
                        landmarks[landmark_name][axis] = float(value)
                    except (ValueError, TypeError):
                        pass

                # Also get visibility
                vis_col = f"landmark_{landmark_name}_visibility"
                vis_value = row.get(vis_col, '')
                if vis_value and vis_value != '' and 'visibility' not in landmarks[landmark_name]:
                    try:
                        landmarks[landmark_name]['visibility'] = float(vis_value)
                    except (ValueError, TypeError):
                        pass

            # Extract angles
            angles = {}
            for angle_name in ALL_ANGLE_NAMES:
                col_name = f'angle_{angle_name}'
                value = row.get(col_name, '')
                if value and value != '':
                    try:
                        angles[angle_name] = float(value)
                    except (ValueError, TypeError):
                        pass

            frames.append({
                'frame_number': frame_number,
                'timestamp_ms': timestamp_ms,
                'landmarks': landmarks,
                'angles': angles,
            })

    return frames


def get_landmark_position(landmarks: dict, name: str) -> tuple[float, float] | None:
    """
    Get (x, y) position for a landmark if it exists and has valid coordinates.

    Args:
        landmarks: Dict of landmark data from a frame
        name: Landmark name (e.g., 'left_shoulder')

    Returns:
        (x, y) tuple or None if landmark not found or incomplete
    """
    if name not in landmarks:
        return None
    lm = landmarks[name]
    if 'x' in lm and 'y' in lm:
        return (lm['x'], lm['y'])
    return None


def get_landmark_visibility(landmarks: dict, name: str) -> float:
    """
    Get visibility score for a landmark (0.0 to 1.0).

    Args:
        landmarks: Dict of landmark data from a frame
        name: Landmark name

    Returns:
        Visibility score, or 0.0 if not found
    """
    if name not in landmarks:
        return 0.0
    return landmarks[name].get('visibility', 0.0)
