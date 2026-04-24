# UI_Final

SquatCheck HW10 Flask prototype - a learning module for identifying squat compensation patterns.

## Skeleton Animation System

The app supports animated skeleton players driven by real MediaPipe pose data.

### Regenerating skeleton data

The full pipeline: **video → pose CSV → skeleton JSON**

#### 1. Set up dynalytix (one-time)

```bash
# Clone next to this repo
git clone --branch fms-demo https://github.com/Jolieabadir/dynalytix.git ../dynalytix

# Or set the path explicitly
export DYNALYTIX_PATH=/path/to/your/dynalytix
```

#### 2. Add videos

Drop video files into `videos/` (this folder is gitignored):
- `good_squat.mov` — clean squat with no compensations
- `heel_rise.mov` — squat with heels lifting
- `forward_lean.mov` — excessive torso forward lean
- `lumbar_flexion.mov` — lower back rounding at depth

#### 3. Build all skeletons

```bash
python scripts/build_all.py
```

This will:
1. Extract pose data from videos → `data/pose_csvs/*.csv`
2. Convert to skeleton JSON → `static/skeletons/*.json`
3. Print orientation sanity check for each

#### 4. Other commands

```bash
# Build single clip
python scripts/build_all.py --only good_squat

# Force re-extraction (even if CSV exists)
python scripts/build_all.py --force

# List configured clips and status
python scripts/build_all.py --list

# Convert existing CSV manually
python scripts/csv_to_skeleton.py data/pose_csvs/good_squat.csv static/skeletons/good_squat.json \
    --label "Good Squat" --frames 45:120 --downsample 2 --mirror
```

### What gets committed

| Folder | Committed? | Contains |
|--------|------------|----------|
| `videos/` | No | Source video files (large binaries) |
| `data/pose_csvs/` | Yes | Extracted pose data (small text) |
| `static/skeletons/` | Yes | Player-ready JSON (small text) |

### CSV to JSON Converter Options

| Option | Description |
|--------|-------------|
| `--downsample N` | Keep every Nth frame (default: 2, so 30fps becomes 15fps) |
| `--frames START:END` | Trim to specific frame range (e.g., `45:120`) |
| `--label NAME` | Human-readable label for the skeleton |
| `--mirror` | Flip horizontally so all skeletons face the same direction |

### Adding Skeletons to Lessons

In `data/lessons.json`, add a `skeleton` field alongside the existing `image` field:

```json
{
  "id": 3,
  "title": "Heel Position",
  "type": "comparison",
  "good": {
    "image": "heel_good.png",
    "skeleton": "good_squat.json",
    "caption": "Heels flat on ground"
  },
  "bad": {
    "image": "heel_bad.png",
    "skeleton": "heel_rise.json",
    "caption": "Heels lifted off ground"
  },
  "tip": "..."
}
```

If `skeleton` is present, the player renders; otherwise falls back to the image.

### Running Tests

```bash
python scripts/test_skeleton_render.py
```

This verifies:
- All learn pages render without errors
- Skeleton JSON files are valid
- Required static files exist