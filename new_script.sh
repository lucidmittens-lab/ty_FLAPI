#!/usr/bin/env bash
# Create scripts/<name>/ from scripts/_template.
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <script-name>   (lowercase-hyphen, e.g. export-shot-list)" >&2
    exit 1
fi

name="$1"
if [[ ! "$name" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
    echo "Script name must be lowercase letters/digits separated by hyphens." >&2
    exit 1
fi

root="$(cd "$(dirname "$0")" && pwd)"
dest="$root/scripts/$name"
if [ -e "$dest" ]; then
    echo "$dest already exists." >&2
    exit 1
fi

mkdir -p "$dest"
sed "s/SCRIPT_NAME/$name/g" "$root/scripts/_template/script.py" > "$dest/$name.py"
sed -e "s/SCRIPT_NAME/$name/g" -e "s/YYYY-MM-DD/$(date +%F)/" "$root/scripts/_template/README.md" > "$dest/README.md"
chmod +x "$dest/$name.py"

echo "Created $dest"
