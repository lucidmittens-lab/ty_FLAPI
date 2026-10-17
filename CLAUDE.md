# Notes for Claude

This repo is a collection of independent FilmLight API (FLAPI) scripts, not a
single application. Read README.md for the layout and versioning rules. In short:

- Each script lives in `scripts/<name>/<name>.py` with its own `README.md`.
- To change a script, edit that file in place. Do not create `_v2` copies.
  Bump `__version__` and add an entry to the Changelog in the script's README.
- Create new scripts with `./new_script.sh <name>`.
- `flapi` ships with FilmLight software and is not installed here, so scripts
  can't be run end to end in this environment. At minimum, check syntax with
  `python3 -m py_compile`.
- Keep scripts standalone. Don't add shared modules unless asked.
