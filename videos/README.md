# Local video files

Drop your squat videos here. These files are gitignored — they don't get committed.

## Required filenames (match `scripts/build_all.py` CLIPS config):

- `good_squat.mov` — clean squat with no compensations
- `heel_rise.mov` — squat with heels lifting at the bottom
- `forward_lean.mov` — squat with excessive torso forward lean
- `lumbar_flexion.mov` — squat with lower back rounding at depth

## Supported formats

Any format that MediaPipe/OpenCV can read: `.mov`, `.mp4`, `.avi`, etc.

## To regenerate skeleton data after adding/replacing videos:

```bash
python scripts/build_all.py
```

This produces:
- CSVs in `data/pose_csvs/` (pose data extracted from videos)
- JSONs in `static/skeletons/` (ready for the skeleton player)

Both CSV and JSON files **DO get committed** so teammates don't need the videos.

## Single clip only

```bash
python scripts/build_all.py --only good_squat
```

## Force re-extraction

```bash
python scripts/build_all.py --force
```

## Check what's configured

```bash
python scripts/build_all.py --list
```
