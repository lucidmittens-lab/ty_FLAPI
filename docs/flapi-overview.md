# FLAPI overview: what scripts can read and change

A summary of the FilmLight Python API, written from FilmLight's
[Python API reference](https://www.filmlight.ltd.uk/support/documents/filmlightapi/docs/python.html)
(the copy for Baselight/Daylight 7.0, wheel `filmlightapi-7.0.0.24522`, read
2026-10-17). The reference is the source of truth for exact signatures and
types. This page is for finding the right class quickly.

Methods marked **BETA** in the reference can change between releases.

---

## 1. The basics every script needs

**Connecting**

```python
import flapi
conn = flapi.Connection()                          # local: the token is found automatically
conn = flapi.Connection("host", username="u", token="...")   # remote host
conn.connect()
...
conn.close()
```

- Remote connections need a token. Create one on the server with
  `/usr/fl/baselight/bin/fl-setup-flapi-token`. It is stored in
  `~/.filmlight/flapi-token` (Linux) or
  `~/Library/Preferences/FilmLight/flapi-token` (macOS).
- Classes are reached through the connection, for example
  `conn.Scene.open_scene(...)` or `conn.JobManager.get_jobs("localhost")`.
- **Release what you create.** Every object you get back (Scene, Shot,
  SequenceDescriptor, QueueManager and so on) lives on the server until you
  call `.release()` or close the connection. Long-running scripts must release
  Shot objects in loops, or they leak.
- Errors are raised as `flapi.FLAPIException`. Server logs are in
  `/usr/fl/log/<hostname>-flapid/console.txt`.

**Python environment.** `flapi` is a wheel, not something you add to the path.
Baselight creates a virtual environment that has it installed:

- Linux: `/usr/fl/python/3.12-rocky-8-v7-venv/bin/python3`
- macOS: `/Library/Application Support/FilmLight/python/3.12-v7-venv/bin/python3`

To run scripts from another machine, `pip install` the wheel from
`/usr/fl/baselight/share/flapi/python/` into your own Python 3.12
virtual environment.

**Editing a scene uses deltas.** Every change is wrapped in a transaction that
can be undone:

```python
scene = conn.Scene.open_scene(conn.Scene.parse_path("localhost:myjob:myscene"))
scene.start_delta("Set shot categories")   # this name shows in the undo history
# ... set_* / insert_* calls ...
scene.end_delta()                          # or cancel_delta() to roll back
scene.save_scene()
```

- Only one interface can hold a scene read/write at a time. Use
  `OPENFLAG_READ_ONLY` for report-type scripts so you never take the lock.
- Scripts running *inside* Baselight that change the scene currently open in
  the UI need `scene.set_transient_write_lock_deltas(1)` (BETA). Keep those
  deltas short, because while one is open the user can't make edits.
- Other open flags: `DISCARD`, `RECOVER` (unsaved changes), `OLD`,
  `IGNORE_REVISION`, `ALLOW_UNKNOWN_OFX` and `NO_CONTAINER_WARNING`.

---

## 2. Database: jobs, folders, scenes (`JobManager`)

All of these are static calls that take a host:

| Read | Change |
|---|---|
| `get_jobs`, `get_folders` (can recurse), `get_scenes` | `create_job`, `rename_job`, `delete_job` |
| `get_scene_info` (`SceneInfo`) | `create_folder`, `rename_folder`, `delete_folder` |
| `job_exists`, `scene_exists` | `rename_scene`, `delete_scene` |

You create or open scenes through `Scene`: `new_scene(path, options)`, where
the options set the format, colour space, frame rate and field order;
`open_scene`; and `temporary_scene()`, an in-memory scene that is never saved
to the database. Temporary scenes are useful for one-off renders or
transcodes. Each of these also has a `_nonblock` version that fires signals
when it finishes.

---

## 3. Scene-level data (`Scene`, `SceneSettings`)

**Readable**

- Identity: `get_scene_pathname()`, `get_scene_container()`, `is_read_only()`.
- Timeline: `get_start_frame/get_end_frame`, `get_working_frame_rate`,
  `get_record_timecode_for_frame`.
- Shots: `get_num_shots`, `get_shot_ids(first, last)` (returns `ShotInfo`),
  `get_shot_id_at(frame)`, `get_shot_index_range(start, end)` and
  `get_shot(id)`, which returns a Shot object.
- Timeline marks: `get_num_marks`, `get_mark_ids`, `get_mark_ids_in_range` and
  `get_mark(id)`. A Mark has a type, position, time, note text, colour,
  category, source and record frame and timecode, and a properties dict.
- Categories: `get_mark_categories`, `get_strip_categories`, `get_category(key)`.
- Metadata schema: `get_metadata_definitions()` returns a list of
  `MetadataItem` (Key, Name, Type, NumElements, IsReadOnly, IsUserDefined,
  Properties). **Start here to find out which per-shot metadata keys exist.**
- Formats and colour: `get_formats()` returns a `FormatSet`, and
  `Scene.get_look_names()` / `get_look_infos()` list the available Looks.
- Custom data: `get_custom_data(key)` / `get_custom_data_keys()`.

**Changeable**

- Edit the timeline: `insert_sequence` (media), `insert_blank`, `insert_bars`,
  `insert_text`, and `delete_shot(id, cleanup, closeGap)`.
  `stereo_combine_shots` handles stereo.
- Marks: `add_mark(frame, category, note)` and `delete_mark(id)`. Existing
  marks are changed with `Mark.set_properties`.
- Categories: `set_category(name, colour)` adds or overwrites one.
- Metadata schema: `add_metadata_defn(name, type)`, `delete_metadata_defn`, and
  `set_metadata_defn_property`. This lets you add your own columns.
- Container: `set_scene_container`.
- Custom data: `set_custom_data(key, value)`. This is a private key/value store
  for your scripts. It **doesn't need a delta and isn't affected by undo**,
  which makes it good for recording things like "processed by script X at
  version Y".

**Scene settings** (`scene.get_scene_settings()`, then `get/set`,
`get_single/set_single`) apply to every shot:

- Format and timing: `WorkingFormat`, `WorkingFrameRate`, `WorkingFieldOrder`,
  `StartTimecode`, `StartKeycode`, `KeycodeGearing`.
- Colour pipeline: `WorkingColourSpace`, `GradeResultColourSpace`,
  `InputColourSpace` (the default for new media), `InputColourSpacePreferAutomatic`,
  `DisplayRenderingTransform`, `ApplyInverseDRTs`, `MasteringColourSpace`,
  `MasteringOperation`, `MasteringWhitePoint`, `CAT`, `HDRClipBehaviour`.
- HDR and stereo: `DolbyVisionMode`, `DolbyVisionMasteringDisplay`, `StereoMode`.
- Resampling: `TemporalSamplingMode`, `OpticalFlowQuality/Smoothing`,
  `ImageTransformMode/Sharpness/Space/ClampNegative`.
- Other: `TimelineCaching`, `AutoProxySourceResolution`, `AutoUpdateFormats`.

`get_setting_keys()` and `get_setting_definition(key)` list what your version
supports.

---

## 4. Shot-level data (`Shot`)

A Shot is the top strip, usually the media, plus the strips stacked under it.

**Readable**

- Timing: `get_start_frame/get_end_frame/get_poster_frame` and
  `get_start_timecode/get_end_timecode/get_timecode_at_frame` (timeline/record),
  `get_src_start_frame/get_src_end_frame`, `get_src_*_timecode` and
  `get_src_*_keycode` (source), and `get_frame_rate`.
- Media: `get_sequence_descriptor()` returns a `SequenceDescriptor` with the
  path, filename pattern, width, height and pixel aspect ratio, start/end
  timecode (two tracks), keycode, handles, tape name, EXR channels, movie
  frame rate, audio channels and rate, `has_blg`, and `get_metadata()`, the
  raw metadata read from the media. `get_codec()` also works.
- Metadata: `get_metadata(keys)` / `get_metadata_strings(keys)`, using keys
  from `Scene.get_metadata_definitions()`.
- Colour and format: `get_input_colour_space`, `get_actual_input_colour_space`,
  `input_colour_space_derived_from_media`, `aces_idt_for_input_colour_space`,
  `get_input_format`, `get_input_video_lut`, `get_input_orientation`,
  `get_fdl(output_format)`.
- Grade: `get_blg_payload()` and `get_blg_resources()`, which return the whole
  stack as a BLG blob. `get_matte_references()` lists the mattes and channels
  the shot uses.
- Categories and marks: `get_categories()`, `get_num_marks`, `get_mark_ids`,
  `get_mark`. Shot marks are on source frames and can be per eye.
- Client review data: `get_client_event_list(frame)` (notes and flags),
  `get_client_event_list_frames`, `get_client_data_summary`,
  `get_client_event_metadata`.
- Decode: `get_decode_parameters()`. For example, RAW decode settings.
  `Shot.get_decode_parameter_definitions(type)` lists the keys.
- Audio: `get_audio_settings()`.

**Changeable**

- Metadata: `set_metadata({key: value})`. This is the main way to change
  per-shot information.
- Categories: `set_categories(set)`.
- Marks: `add_mark(frame, category, note, eye)` and `delete_mark`.
- Input: `set_input_colour_space`, `set_stack_colour_space`,
  `set_input_format`, `set_input_video_lut`, `set_input_orientation`,
  `set_input_format_from_fdl(fdl, options)`, and
  `create_format_from_fdl_canvas_template`.
- Decode and audio: `set_decode_parameters({...})`, which can be partial, and
  `set_audio_settings`.
- Mattes: `update_matte_references` renames matte channels in Reference
  operators.
- Client review: `add_client_note`, `add_client_flag`, `delete_client_event`,
  `set_client_event_metadata`, `delete_frame_client_event_list`.

**Grade levers.** These **add layers** to the stack. Unless noted, they insert
at the bottom.

| Method | What it adds |
|---|---|
| `insert_cdl_layer([sR,sG,sB, oR,oG,oB, pR,pG,pB, sat])` | ASC CDL layer. `insert_cdl_layer_above` puts it at the top |
| `insert_basegrade_layer({...})` | BaseGrade with these keys: `BalanceExposure/A/B`, `Flare`, `Saturation`, `Contrast`, `ContrastPivot`, and `Light/Dim/Bright/Dark` × `Exposure/A/B/Pivot/Falloff/Saturation` |
| `insert_look_layer(name)` | A named Look |
| `insert_lut_layer(location, file, inCS, outCS, ...)` | LUT operator |
| `insert_truelight_layer(lut_path)` | Truelight 1D/3D LUT |
| `insert_colour_space_layer(toCS, drt, identify)` | Colour space conversion |
| `insert_shape_layer_from_svg(svg, fit, mask_format, mask)` | A shape layer drawn from an SVG |
| `insert_blg_stack(path)` / `apply_blg_payload(payload, resources)` | The whole stack from a BLG file or blob |
| `insert_amf_stack(amf_path, settings)` | ACES AMF pipeline |
| `delete_all_layers()` | Clears the stack |

> **Limitation.** I found no methods in this API for reading or changing a
> parameter on an *existing* layer, for example "change the exposure on layer
> 2". You can add layers, clear the stack, or move a whole grade around as
> BLG. To change existing grades in bulk, the usual approach is
> `get_blg_payload`, then editing or replacing it, then `apply_blg_payload`,
> or using MultiPaste (section 5).

---

## 5. Bulk operations

- **MultiPaste** (`MultiPaste.create()`, then `multi_paste(scene, settings, shot_ids)`)
  copies grades and metadata in, matched by clip, tape or timecode and so on.
  The source can be other database scenes, a BLG folder, an EDL (optionally
  applying its ASC CDLs), CDL/CCC files, or AMF files. Matching rules, layer
  handling and conflict resolution are all set through `MultiPasteSettings`.
- **Export** (`Export.create()`, then `select_*`, then `do_export_*`) writes
  BLG, CDL, AMF, cube LUT or stills for selected shots. It runs on a queue.
- **AudioSync** (`AudioSync.create()`, then `audio_sync(...)`) syncs audio by
  timecode or metadata.

---

## 6. Rendering and the queue

- **`RenderSetup`**: `create_from_scene(scene)` loads the scene's own
  deliverables, or you can build them with `add_deliverable(RenderDeliverable)`.
  A deliverable sets the file type, codec, image options, output directory or
  container, filename prefix, postfix and padding, render format and
  resolution, frame rate, colour space, burn-ins, masks and so on.
- **Choosing what to render**: `select_all`, `select_shots`, `select_shot_ids`,
  `select_graded_shots`, `select_shots_of_category`, `select_timeline_marks`,
  `select_shot_marks`, `select_poster_frames`, `set_frames(ranges)`.
- **Running it**: `submit_to_queue(queue, name)` sends it to a queue, or
  `RenderProcessor.get().start(setup)` renders in-process with
  `get_progress()`. `save_into_scene(scene)` keeps your deliverables in the
  scene.
- **`QueueManager`** (`create_local()`, `create(zone)`, `get_queue_zones()`):
  list operations, get their status and logs, and pause, resume, restart,
  delete or archive them. `enable_updates()` turns on live signals. As a
  BETA feature you can also define **custom queue operations**
  (`new_operation`, `get_next_task`, `set_task_done`...) to build your own
  workers.

---

## 7. Formats, framing, colour spaces

- `FormatSet.factory_formats()`, `global_formats()`, `job_formats(host, job)`
  or `scene.get_formats()` let you list, add or delete formats and list
  colour spaces (`get_colour_space_names/info`). `get_drt_names/info` lists
  the display rendering transforms.
- `Format`: resolutions, mappings to other formats, **masks**
  (add/delete) and **burn-ins** (`FormatBurnin`, where you set the font,
  opacity, box colour and text items).
- `FDL`: load, validate, create, merge and save ASC Framing Decision Lists, and
  turn a canvas into a Format.

---

## 8. Working with the live application (scripts run inside Baselight)

- `Application`: application and SDK info, `is_playing`, the clipboard,
  `open_url`, and app-wide custom data. As BETA features it can also give
  `get_current_scene()`, `get_open_scene_names()`, `get_current_cursor()`,
  `log()` to the Log view, `message_dialog`, and `list_dialog`.
  Signals: `SceneOpened`, `SceneClosed`, `PlayModeChanged`.
- `CurrentGrade.get()`: the `UpdateCurrentShot` signal (cursor, scene and
  shot id) fires when the grader moves to a different shot. This is the hook
  for "follow the colourist" tools.
- `Cursor`: timeline time, frame and record timecode, the viewing format,
  mask, and whether Truelight is on.
- UI (all BETA): `MenuItem.create(title, key).register(location)` adds menu
  entries to the app, Scene, Edit, Job Manager, Shots View or FLUX Manage
  menus. Also `DynamicDialog` (forms), `ProgressDialog`, and `Timer`.
- `FLUXManage.get()`: the sequences and files selected in the browser.
- `ThumbnailManager`: URIs for poster and scrub thumbnails.
- `ClientViewManager`: Client View session, clients and stream settings.

---

## 9. Utilities

- `Image.get_raw_metadata(path)` reads metadata from any file without needing
  a scene.
- `SequenceDescriptor.get_for_template(...)`, `get_for_template_with_timecode`
  and `get_for_file` scan the filesystem for media. They can also
  `trim_movie`.
- `Utilities.timecode_from_string` and `get_allowed_enum_values`.
- `Volumes`, `Licence`.

---

## Script ideas this enables

- Shot list or metadata report to CSV/HTML (read-only open, then shots,
  metadata and the sequence descriptor).
- Bulk-set metadata, categories or input colour spaces from a spreadsheet.
- Turn client notes or marks into a review list. Turn a list into marks.
- Apply CDLs from an EDL or CCC across a conform (MultiPaste, or
  `insert_cdl_layer`).
- Build a scene from a folder of media (`get_for_template` →
  `insert_sequence`).
- Render or watch the queue, and send a notification when it finishes.
- Menu-item tools inside Baselight that act on the current scene or shot.
