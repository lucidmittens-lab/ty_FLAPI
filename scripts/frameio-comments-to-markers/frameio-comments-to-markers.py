#!/usr/bin/env python3
"""
frameio-comments-to-markers - add Frame.io CSV comments to a Baselight scene as markers.

Reads a comment CSV exported from Frame.io, adds each comment as a marker in the
[FRAME.IO] category of the given scene, saves the scene, and prints an EDL of the
shots that have comments, for metadata transfer via multipaste.

Markers are placed using the Timecode Source column of the Frame.io CSV.

Usage:
    python3 frameio-comments-to-markers.py host:job:scene /path/to/frameio_comments.csv
"""

__version__ = "1.1.0"

import argparse
import csv
import os
import sys

try:
    import flapi
except ImportError:
    sys.exit("Could not import flapi. Run with Baselight's FLAPI Python venv, or pip install the filmlightapi wheel.")

FPS = 24
MARK_CATEGORY = "[FRAME.IO]"
MARK_COLOUR = [88/255.0, 91/255.0, 88/255.0, 246/255.0]  # Frame.io's web color

# Frame.io CSV column indexes
COL_AUTHOR = 5
COL_COMMENT = 7
COL_DATE_TIME = 9
COL_FRAME = 12
COL_FRAMEIO_TIMECODE = 14
COL_TIMECODE_SOURCE = 17


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("scene", help="Scene path, as host:job:scene")
    parser.add_argument("csv_path", help="Path to the Frame.io comments CSV")
    parser.add_argument("--host", default="localhost", help="FLAPI server host (default: localhost)")
    parser.add_argument("--user", help="Username, needed for remote hosts")
    parser.add_argument("--token", default=os.environ.get("FLAPI_TOKEN"),
                        help="FLAPI token, needed for remote hosts (default: $FLAPI_TOKEN)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def timecode_difference_to_frames(start_tc, end_tc):
    """Calculate frame difference between two timecodes at 24fps"""
    try:
        # Parse start timecode
        start_parts = start_tc.split(':')
        if len(start_parts) != 4:
            return None
        start_h, start_m, start_s, start_f = map(int, start_parts)
        start_total_frames = (start_h * 3600 + start_m * 60 + start_s) * FPS + start_f

        # Parse end timecode
        end_parts = end_tc.split(':')
        if len(end_parts) != 4:
            return None
        end_h, end_m, end_s, end_f = map(int, end_parts)
        end_total_frames = (end_h * 3600 + end_m * 60 + end_s) * FPS + end_f

        # Return difference
        return end_total_frames - start_total_frames

    except Exception:
        return None


def add_timecodes(tc1, tc2):
    """Add two timecodes together"""
    try:
        h1, m1, s1, f1 = map(int, tc1.split(':'))
        h2, m2, s2, f2 = map(int, tc2.split(':'))

        total_h = h1 + h2
        total_m = m1 + m2
        total_s = s1 + s2
        total_f = f1 + f2

        # Handle frame overflow
        if total_f >= FPS:
            total_s += 1
            total_f -= FPS

        # Handle second overflow
        if total_s >= 60:
            total_m += total_s // 60
            total_s = total_s % 60

        # Handle minute overflow
        if total_m >= 60:
            total_h += total_m // 60
            total_m = total_m % 60

        return f"{total_h:02d}:{total_m:02d}:{total_s:02d}:{total_f:02d}"

    except Exception:
        return None


def frame_to_timecode(frame, fps=FPS):
    total_seconds = frame / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frames = int(frame % fps)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def read_rows(csv_path):
    """Return the CSV rows, without the header row."""
    with open(csv_path, newline='') as csv_file:
        return list(csv.reader(csv_file, delimiter=','))[1:]


def calculate_frame_offset(scene_start_tc, rows):
    """Offset from Frame.io frame numbers to scene frames, using the first usable row."""
    if not scene_start_tc:
        return 0
    for row in rows:
        try:
            frameio_frame = int(row[COL_FRAME])
            timecode_source = row[COL_TIMECODE_SOURCE] if len(row) > COL_TIMECODE_SOURCE else None
            if timecode_source:
                target_scene_frame = timecode_difference_to_frames(scene_start_tc, timecode_source)
                if target_scene_frame is not None:
                    # Baselight frame - Frame.io frame + 1 for frame 0 adjustment
                    return target_scene_frame - frameio_frame + 1
        except Exception:
            continue
    return 0


def add_comment_marks(scene, rows, frame_offset):
    """Add a marker for each comment. Return (comments_processed, edl_events)."""
    comments_processed = 0
    edl_events = []

    for i, row in enumerate(rows, start=1):
        try:
            frame_number = int(row[COL_FRAME])  # Original Frame.io frame number
            scene_frame = frame_number + frame_offset

            comment_text = row[COL_COMMENT]
            author = row[COL_AUTHOR].strip('"')
            date_time = row[COL_DATE_TIME]
            frameio_timecode = row[COL_FRAMEIO_TIMECODE] if len(row) > COL_FRAMEIO_TIMECODE else "N/A"
            timecode_source = row[COL_TIMECODE_SOURCE] if len(row) > COL_TIMECODE_SOURCE else "N/A"

            comment_string = f"On {date_time.split(' ')[0]} at {date_time.split(' ')[1]}, {author} wrote: {comment_text}"

            print(f"Inserting Frame.io comment marker at scene frame {scene_frame} (Frame.io: {frame_number}, TC Source: {timecode_source})")
            scene.add_mark(scene_frame, MARK_CATEGORY, comment_string)

            # Find shot containing this scene frame for EDL generation
            shot_id = scene.get_shot_id_at(scene_frame)
            if shot_id is not None:
                for shot_info in scene.get_shot_ids():
                    if shot_info.ShotId == shot_id:
                        edl_events.append({
                            'event_num': len(edl_events) + 1,
                            'reel': f"R{shot_info.ShotId:03d}",
                            'start_frame': shot_info.StartFrame,
                            'end_frame': shot_info.EndFrame,
                            'comment': comment_string,
                            'frame_io_frame': frame_number,
                            'frame_io_timecode': frameio_timecode,
                            'timecode_source': timecode_source,
                            'scene_frame': scene_frame,
                        })
                        print(f"Added EDL event for shot {shot_info.ShotId} (frames {shot_info.StartFrame}-{shot_info.EndFrame})")
                        break

            comments_processed += 1

        except (ValueError, IndexError) as e:
            print(f"Error processing row {i}: {e}")
            continue
        except Exception as e:
            print(f"Unexpected error processing row {i}: {e}")
            continue

    return comments_processed, edl_events


def print_edl(edl_events, scene_start_tc):
    print(f"\n{'='*60}")
    print("FRAME.IO COMMENTS EDL - Copy and paste below:")
    print(f"{'='*60}")

    print("TITLE: Frame.io Comments")
    print("FCM: NON-DROP FRAME")
    print()

    for event in edl_events:
        # Add scene start timecode to get actual timecodes
        start_tc = add_timecodes(scene_start_tc, frame_to_timecode(event['start_frame']))
        end_tc = add_timecodes(scene_start_tc, frame_to_timecode(event['end_frame']))

        print(f"{event['event_num']:03d}  {event['reel']}       V     C        {start_tc} {end_tc} {start_tc} {end_tc}")
        print(f"* FROM CLIP NAME: SHOT_{event['event_num']:03d}")
        print(f"* COMMENT: {event['comment']}")
        print(f"* FRAME.IO FRAME: {event['frame_io_frame']} (Frame.io TC: {event.get('frame_io_timecode', 'N/A')})")
        print(f"* TIMECODE SOURCE: {event['timecode_source']}")
        print(f"* SCENE FRAME: {event['scene_frame']}")
        print()

    print(f"{'='*60}")
    print("END EDL")
    print(f"{'='*60}")


def run(conn, args):
    # Open the given scene
    scene_path = conn.Scene.parse_path(args.scene)
    try:
        scene = conn.Scene.open_scene(scene_path, {flapi.OPENFLAG_ALLOW_UNKNOWN_OFX})
    except flapi.FLAPIException as ex:
        sys.exit("Error loading scene: %s" % ex)

    scene.start_delta("Insert Frame.io Marker Nodes and Shot Comments")

    # Create a category for Frame.io markers, if necessary
    if MARK_CATEGORY not in scene.get_mark_categories():
        scene.set_category(MARK_CATEGORY, MARK_COLOUR)

    # Get scene start timecode (corresponds to frame 0 in Baselight)
    try:
        scene_start_tc = str(scene.get_record_timecode_for_frame(0))
    except Exception as e:
        print(f"Error getting scene start timecode: {e}")
        scene_start_tc = None

    rows = read_rows(args.csv_path)

    print("Calculating frame offset...")
    frame_offset = calculate_frame_offset(scene_start_tc, rows)
    if frame_offset == 0:
        print("Could not calculate frame offset. Using Frame.io frame numbers directly.")
    else:
        print(f"Frame offset calculated: {frame_offset}")

    print(f"Processing {len(rows)} Frame.io comments...")
    comments_processed, edl_events = add_comment_marks(scene, rows, frame_offset)

    scene.end_delta()

    print(f"\nProcessed {comments_processed} comments")
    print(f"Generated {len(edl_events)} EDL events")
    print("Saving scene...")
    scene.save_scene()

    if edl_events:
        print_edl(edl_events, scene_start_tc)

    scene.close_scene()
    scene.release()

    print("Done!")


def main():
    args = parse_args()
    if not os.path.isfile(args.csv_path):
        sys.exit("Invalid path supplied to csv.")

    if args.user or args.token:
        conn = flapi.Connection(args.host, username=args.user, token=args.token)
    else:
        conn = flapi.Connection(args.host)
    try:
        conn.connect()
    except flapi.FLAPIException as exc:
        sys.exit("Error: %s" % exc)
    print("Connection OK!")

    try:
        run(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
