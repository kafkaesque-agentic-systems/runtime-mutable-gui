#!/bin/sh
# Purpose: fetch the Inter 4.1 font (Regular, Medium and its licence) into crates/mutable-gui/assets/
#          and record their SHA-256 sums (design/STACK.md row "Inter", D-41).
# Usage: sh tools/fetch-inter.sh
# Side effects: downloads Inter-4.1.zip from GitHub into a new temporary directory (removed on
#          exit); overwrites Inter-Regular.ttf, Inter-Medium.ttf, OFL.txt and SHA256SUMS.
# Exit: non-zero when the download fails or one of the three files is not in the archive.
set -eu
cd "$(dirname "$0")/.."

url=https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip
dest=crates/mutable-gui/assets
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

curl -fL -o "$tmp/Inter-4.1.zip" "$url"
unzip -Z1 "$tmp/Inter-4.1.zip" > "$tmp/entries"

mkdir -p "$tmp/out" "$dest"
for name in Inter-Regular.ttf Inter-Medium.ttf LICENSE.txt; do
  # The first archive entry whose base name is exactly $name.
  entry=$(awk -v n="$name" '{ b = $0; sub(/.*\//, "", b); if (b == n) { print; exit } }' "$tmp/entries")
  if [ -z "$entry" ]; then
    echo "$name is not in $url"
    exit 1
  fi
  unzip -j -o -q "$tmp/Inter-4.1.zip" "$entry" -d "$tmp/out"
done

cp "$tmp/out/Inter-Regular.ttf" "$dest/Inter-Regular.ttf"
cp "$tmp/out/Inter-Medium.ttf" "$dest/Inter-Medium.ttf"
cp "$tmp/out/LICENSE.txt" "$dest/OFL.txt"
(cd "$dest" && shasum -a 256 Inter-Regular.ttf Inter-Medium.ttf OFL.txt > SHA256SUMS)
