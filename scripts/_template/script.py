#!/usr/bin/env python3
"""
SCRIPT_NAME - one-line description of what this script does.

Usage:
    python3 SCRIPT_NAME.py --host localhost
"""

__version__ = "0.1.0"

import argparse
import sys

try:
    import flapi
except ImportError:
    sys.exit("Could not import flapi. Add FilmLight's flapi python directory to PYTHONPATH.")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--host", default="localhost", help="FLAPI server host (default: localhost)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args()


def run(conn, args):
    # Script logic goes here.
    pass


def main():
    args = parse_args()
    conn = flapi.Connection(args.host)
    conn.connect()
    try:
        run(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
