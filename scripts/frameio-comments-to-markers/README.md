# frameio-comments-to-markers

Reads a comment CSV exported from Frame.io and adds each comment to a Baselight
scene as a marker in a `[FRAME.IO]` category. It then saves the scene and prints an
EDL of the shots that have comments, which you can paste in for metadata transfer
via multipaste.

Markers are placed using the CSV's **Timecode Source** column. The first usable row
sets an offset between Frame.io frame numbers and scene frames, and that offset is
applied to every comment.

## Requirements

- Tested with: Baselight / Daylight version `X.Y`
- Python 3.12 with `flapi` (Baselight's FLAPI venv, or the filmlightapi wheel)
- A Frame.io comments CSV export with columns in the standard order (author in
  column 6, comment in 8, date/time in 10, frame in 13, Frame.io timecode in 15,
  timecode source in 18)

## Usage

```sh
python3 frameio-comments-to-markers.py host:job:scene /path/to/frameio_comments.csv
```

To connect to a FLAPI server other than `localhost`, pass `--host`, plus
`--user` and `--token` (or set `FLAPI_TOKEN`).

## Known limitations

- Assumes 24 fps non-drop-frame timecode throughout.
- If the offset works out to exactly 0, the script reports that it could not
  calculate one, even though 0 is a valid offset. Marks are placed the same way
  either way.
- If the scene's start timecode can't be read, the EDL timecodes print as `None`.

## Changelog

### 1.1.0 - 2026-10-17
- Added `--user` and `--token` (or `FLAPI_TOKEN`) for remote hosts, matching the
  updated script template.

### 1.0.0 - 2026-10-17
- Imported into this repo from `convert_frameio_comments_to_bl_markers_v41.py`.
- Behaviour unchanged, apart from these changes:
  - Arguments are now parsed with argparse, so `--help` and `--version` work.
  - New `--host` option. It defaults to `localhost`, which the old script had
    hard-coded.
  - The CSV is read once instead of three times.
  - The FLAPI connection is closed when the script finishes.
