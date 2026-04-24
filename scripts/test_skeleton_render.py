#!/usr/bin/env python3
"""
Smoke Test for Skeleton Player

Tests that skeleton players render correctly in learn.html pages.

Usage:
    python scripts/test_skeleton_render.py
"""

import sys
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


def test_learn_pages():
    """Test that all learn pages render without errors."""
    client = app.test_client()

    print("Testing learn pages...")
    print("-" * 40)

    all_passed = True

    for n in range(1, 6):
        response = client.get(f"/learn/{n}")

        if response.status_code != 200:
            print(f"  [FAIL] /learn/{n} - Status {response.status_code}")
            all_passed = False
            continue

        html = response.data.decode("utf-8")

        # Check basic page structure
        if "SquatCheck" not in html:
            print(f"  [FAIL] /learn/{n} - Missing header")
            all_passed = False
            continue

        # For comparison lessons (3, 4, 5), check for either skeleton player or image
        if n >= 3:
            has_skeleton = 'class="skeleton-player"' in html
            has_image = '<img src="/static/img/' in html

            if not has_skeleton and not has_image:
                print(f"  [FAIL] /learn/{n} - Missing both skeleton player and image")
                all_passed = False
                continue

            if has_skeleton:
                # Check that skeleton player JS is included
                if 'skeleton_player.js' not in html:
                    print(f"  [FAIL] /learn/{n} - Skeleton player div present but JS not included")
                    all_passed = False
                    continue
                if 'SkeletonPlayer.initAll()' not in html:
                    print(f"  [FAIL] /learn/{n} - Skeleton player JS missing init call")
                    all_passed = False
                    continue
                print(f"  [PASS] /learn/{n} - Skeleton player renders")
            else:
                print(f"  [PASS] /learn/{n} - Image fallback renders")
        else:
            print(f"  [PASS] /learn/{n} - Intro lesson renders")

    print("-" * 40)

    return all_passed


def test_skeleton_json_files():
    """Test that skeleton JSON files exist and are valid."""
    import json

    skeletons_dir = Path(__file__).parent.parent / "static" / "skeletons"

    print("\nTesting skeleton JSON files...")
    print("-" * 40)

    all_passed = True

    if not skeletons_dir.exists():
        print(f"  [FAIL] Skeletons directory does not exist: {skeletons_dir}")
        return False

    json_files = list(skeletons_dir.glob("*.json"))

    if not json_files:
        print("  [WARN] No skeleton JSON files found")
        return True  # Not a failure, just no files yet

    for json_path in json_files:
        try:
            with open(json_path) as f:
                data = json.load(f)

            # Validate required fields
            required = ["label", "fps", "frames"]
            missing = [k for k in required if k not in data]

            if missing:
                print(f"  [FAIL] {json_path.name} - Missing fields: {missing}")
                all_passed = False
                continue

            if not data["frames"]:
                print(f"  [FAIL] {json_path.name} - No frames")
                all_passed = False
                continue

            # Check first frame structure
            first_frame = data["frames"][0]
            if "joints" not in first_frame:
                print(f"  [FAIL] {json_path.name} - Frame missing 'joints'")
                all_passed = False
                continue

            print(f"  [PASS] {json_path.name} - {len(data['frames'])} frames, {data['fps']} fps")

        except json.JSONDecodeError as e:
            print(f"  [FAIL] {json_path.name} - Invalid JSON: {e}")
            all_passed = False
        except Exception as e:
            print(f"  [FAIL] {json_path.name} - Error: {e}")
            all_passed = False

    print("-" * 40)

    return all_passed


def test_static_files():
    """Test that required static files exist."""
    print("\nTesting static files...")
    print("-" * 40)

    static_dir = Path(__file__).parent.parent / "static"

    files_to_check = [
        ("js/skeleton_player.js", True),
        ("css/skeleton.css", True),
    ]

    all_passed = True

    for rel_path, required in files_to_check:
        full_path = static_dir / rel_path

        if full_path.exists():
            size = full_path.stat().st_size
            print(f"  [PASS] {rel_path} - {size} bytes")
        elif required:
            print(f"  [FAIL] {rel_path} - File not found")
            all_passed = False
        else:
            print(f"  [WARN] {rel_path} - File not found (optional)")

    print("-" * 40)

    return all_passed


def main():
    print("=" * 40)
    print("Skeleton Player Smoke Tests")
    print("=" * 40)

    results = []

    results.append(("Learn Pages", test_learn_pages()))
    results.append(("Skeleton JSONs", test_skeleton_json_files()))
    results.append(("Static Files", test_static_files()))

    print("\n" + "=" * 40)
    print("Summary")
    print("=" * 40)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
