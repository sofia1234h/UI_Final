# UI_Final

SquatCheck HW10 Flask prototype - a learning module for identifying squat compensation patterns.

## Skeleton Animation System

The app supports animated skeleton players driven by real MediaPipe pose data from CSV files.

### Regenerating Skeleton JSONs

When you record new videos and want to update the skeleton animations:

1. **Ensure the dynalytix repo is available:**
   ```bash
   # If not already cloned:
   git clone --branch fms-demo --depth 1 https://github.com/Jolieabadir/dynalytix.git ../dynalytix

   # Or if already cloned, update:
   cd ../dynalytix && git checkout fms-demo && git pull
   ```

2. **List available CSVs:**
   ```bash
   python scripts/build_all_skeletons.py --list
   ```

3. **Auto-generate samples (quick test):**
   ```bash
   python scripts/build_all_skeletons.py --auto
   ```
   This converts the first 5 CSVs to `sample_1.json` through `sample_5.json`.

4. **Interactive mode (for production):**
   ```bash
   python scripts/build_all_skeletons.py
   ```
   This prompts you to map each CSV to a lesson (good_squat, heel_rise, etc.) and specify frame ranges.

5. **Convert a single CSV manually:**
   ```bash
   python scripts/csv_to_skeleton.py <input.csv> static/skeletons/<output.json> \
       --label "Good Squat" \
       --frames 45:120 \
       --downsample 2 \
       --mirror
   ```

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