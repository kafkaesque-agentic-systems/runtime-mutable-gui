#!/bin/sh
# Purpose: CLAP conformance gate. Runs clap-validator 0.4.1 on the bundled reference plugin.
# Usage: cargo xtask bundle mutable-gui-reference --release && sh tools/validate-clap.sh
# Output: the failed tests as JSON in target/clap-validator.json, and on stdout when any failed.
# Exit: 0 when no test failed (clap-validator prints {"results": []}), 1 otherwise.
set -u
cd "$(dirname "$0")/.." || exit 1

bundle=target/bundled/mutable-gui-reference.clap
report=target/clap-validator.json

if [ ! -d "$bundle" ]; then
  echo "$bundle is missing: run cargo xtask bundle mutable-gui-reference --release"
  exit 1
fi

clap-validator -v quiet validate --json --only-failed "$bundle" > "$report"

if python3 -c 'import json, sys; sys.exit(0 if json.load(open(sys.argv[1])).get("results") == [] else 1)' "$report"; then
  exit 0
fi
echo "clap-validator reported failures (also in $report):"
cat "$report"
exit 1
