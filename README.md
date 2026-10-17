# ty_FLAPI

A collection of small, standalone scripts that use the **FilmLight API (FLAPI)**
to automate jobs in Baselight / Daylight.

This isn't one application. Each script is self-contained, has its own folder,
and is versioned on its own.

## Layout

```
scripts/
  _template/            copy this to start a new script
    script.py
    README.md
  <script-name>/
    <script-name>.py    the current version of the script
    README.md           what it does, how to run it, changelog
new_script.sh           sets up a new script folder from the template
```

## Starting a new script

```sh
./new_script.sh render-queue-report
```

This creates `scripts/render-queue-report/` with a starter
`render-queue-report.py` and a `README.md`.

## Versioning

Git keeps the history, so each script has **one** current file. There are no
`_v2_final_FINAL.py` copies.

1. **Iterate** by editing `scripts/<name>/<name>.py` and committing.
2. **Record** each meaningful change in the **Changelog** section of the
   script's `README.md`, and bump `__version__` at the top of the script.
3. **Mark a known-good version** with a per-script tag:
   ```sh
   git tag <name>/v1.2.0
   git push origin <name>/v1.2.0
   ```
4. **Get an old version back** without touching the current one:
   ```sh
   git show <name>/v1.0.0:scripts/<name>/<name>.py > /tmp/<name>_v1.0.0.py
   git log --oneline -- scripts/<name>/      # history of one script
   ```

Version numbers: `MAJOR.MINOR.PATCH`. Bump MAJOR when the arguments or
behaviour change in a way that breaks existing use, MINOR for new features,
and PATCH for fixes.

## Running scripts

The scripts need the `flapi` Python module that ships with FilmLight software.
It is not on PyPI. Point Python at the copy that came with your install, for
example:

```sh
export PYTHONPATH=/usr/fl/baselight/share/flapi/python:$PYTHONPATH   # adjust for your install/version
python3 scripts/<name>/<name>.py --help
```

FLAPI's calls change between FilmLight releases, so each script's README says
which Baselight/Daylight version it was tested against.

## Conventions

- Script folders use lowercase-hyphen names, such as `export-shot-list`.
- Every script accepts `--host` (default `localhost`) and has `--help`.
- Never commit credentials. Pass them as arguments or environment variables.
- If code ends up copied into three or more scripts, consider moving it into a
  shared `common/` module. Until then, keep scripts standalone so each one can be
  copied to a machine and run on its own.
