#!/usr/bin/env python3
"""
Batch Skeleton Builder

Builds skeleton JSON files from all available CSVs in the dynalytix repo.

Usage:
    python build_all_skeletons.py --auto        # Auto-mode: first 5 CSVs as samples
    python build_all_skeletons.py               # Interactive mode: choose mappings
    python build_all_skeletons.py --list        # Just list available CSVs
"""

import argparse
import sys
from pathlib import Path

# Add scripts dir to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from csv_to_skeleton import convert_csv_to_skeleton

# Where to find CSVs
DYNALYTIX_DATA_PATHS = [
    Path(__file__).parent.parent.parent.parent / "dynalytix" / "data_collection" / "backend" / "data",
    Path.home() / "dynalytix" / "data_collection" / "backend" / "data",
]

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "static" / "skeletons"

# Lesson mappings for interactive mode
LESSON_SKELETON_NAMES = [
    ("good_squat", "Good Squat"),
    ("heel_rise", "Heel Rise Compensation"),
    ("forward_lean", "Forward Lean Compensation"),
    ("knee_valgus", "Knee Valgus Compensation"),
    ("lumbar_flexion", "Lumbar Flexion Compensation"),
]


def find_data_dir() -> Path:
    """Find the dynalytix data directory."""
    for path in DYNALYTIX_DATA_PATHS:
        if path.exists():
            return path
    return None


def list_csvs(data_dir: Path) -> list[tuple[str, int]]:
    """List all CSVs with their frame counts."""
    csvs = []
    for csv_path in sorted(data_dir.glob("*.csv")):
        with open(csv_path) as f:
            line_count = sum(1 for _ in f) - 1  # Subtract header
        csvs.append((csv_path.name, line_count))
    return csvs


def auto_mode(data_dir: Path):
    """Auto mode: convert first 5 CSVs to sample JSONs."""
    csvs = list_csvs(data_dir)

    if not csvs:
        print("No CSV files found!")
        return

    print(f"Auto mode: Converting first {min(5, len(csvs))} CSVs...")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for i, (csv_name, frame_count) in enumerate(csvs[:5]):
        input_path = data_dir / csv_name
        output_name = f"sample_{i + 1}.json"
        output_path = OUTPUT_DIR / output_name

        print(f"  [{i + 1}] {csv_name} ({frame_count} frames)")

        try:
            result = convert_csv_to_skeleton(
                input_path=input_path,
                output_path=output_path,
                label=f"Sample {i + 1}",
                downsample=2,
            )
            print(f"      -> {output_name} ({len(result['frames'])} frames after downsampling)")
        except Exception as e:
            print(f"      ERROR: {e}")

    print()
    print(f"Output directory: {OUTPUT_DIR}")


def interactive_mode(data_dir: Path):
    """Interactive mode: let user map CSVs to lessons."""
    csvs = list_csvs(data_dir)

    if not csvs:
        print("No CSV files found!")
        return

    print("Available CSV files:")
    print("-" * 60)
    for i, (csv_name, frame_count) in enumerate(csvs):
        print(f"  [{i + 1:2}] {csv_name}")
        print(f"       {frame_count} frames")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for skeleton_key, skeleton_label in LESSON_SKELETON_NAMES:
        print(f"\n{'=' * 60}")
        print(f"Mapping: {skeleton_label}")
        print("=" * 60)

        while True:
            try:
                choice = input(f"Enter CSV number (1-{len(csvs)}) or 's' to skip: ").strip()
                if choice.lower() == 's':
                    print("  Skipped.")
                    break

                idx = int(choice) - 1
                if idx < 0 or idx >= len(csvs):
                    print("  Invalid number. Try again.")
                    continue

                csv_name = csvs[idx][0]
                frame_count = csvs[idx][1]

                print(f"  Selected: {csv_name} ({frame_count} frames)")

                # Ask for frame range
                frame_range_str = input("  Frame range (e.g., 45:120) or Enter for full clip: ").strip()
                frame_range = None
                if frame_range_str:
                    parts = frame_range_str.split(":")
                    start = int(parts[0]) if parts[0] else 0
                    end = int(parts[1]) if len(parts) > 1 and parts[1] else None
                    frame_range = (start, end)

                # Ask for mirror
                mirror_str = input("  Mirror? (y/N): ").strip().lower()
                mirror = mirror_str == 'y'

                # Convert
                input_path = data_dir / csv_name
                output_path = OUTPUT_DIR / f"{skeleton_key}.json"

                result = convert_csv_to_skeleton(
                    input_path=input_path,
                    output_path=output_path,
                    label=skeleton_label,
                    downsample=2,
                    frame_range=frame_range,
                    mirror=mirror,
                )

                print(f"  -> Created {skeleton_key}.json ({len(result['frames'])} frames)")
                break

            except ValueError as e:
                print(f"  Error: {e}")
            except KeyboardInterrupt:
                print("\n\nAborted.")
                return

    print(f"\nOutput directory: {OUTPUT_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Batch build skeleton JSONs")
    parser.add_argument(
        "--auto", action="store_true",
        help="Auto mode: convert first 5 CSVs as samples"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Just list available CSVs"
    )
    args = parser.parse_args()

    data_dir = find_data_dir()
    if data_dir is None:
        print("Error: Could not find dynalytix data directory.", file=sys.stderr)
        print("Expected at one of:", file=sys.stderr)
        for path in DYNALYTIX_DATA_PATHS:
            print(f"  {path}", file=sys.stderr)
        sys.exit(1)

    print(f"Data directory: {data_dir}")
    print()

    if args.list:
        csvs = list_csvs(data_dir)
        print(f"Found {len(csvs)} CSV files:")
        print("-" * 60)
        for i, (csv_name, frame_count) in enumerate(csvs):
            print(f"  [{i + 1:2}] {csv_name}")
            print(f"       {frame_count} frames")
    elif args.auto:
        auto_mode(data_dir)
    else:
        interactive_mode(data_dir)


if __name__ == "__main__":
    main()
