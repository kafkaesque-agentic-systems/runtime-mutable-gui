#!/bin/sh
# Purpose: check that this Mac has the toolchain and tools pinned in design/STACK.md.
# Usage: sh tools/check-env.sh   (prints one line per failed check; prints nothing when all pass)
# Exit: 0 when every check passes, 1 otherwise. Side effects: none.
set -u

failed=0
fail() {
  echo "$1"
  failed=1
}

case "$(rustc +1.99.1 --version 2>/dev/null)" in
  *1.99.1*) ;;
  *) fail "rustc 1.99.1 is missing: run sh setup-prerequisites.sh" ;;
esac
cargo +1.99.1 fmt --version > /dev/null 2>&1 || fail "rustfmt for Rust 1.99.1 is missing: run sh setup-prerequisites.sh"
cargo +1.99.1 clippy --version > /dev/null 2>&1 || fail "clippy for Rust 1.99.1 is missing: run sh setup-prerequisites.sh"
case "$(clap-validator --version 2>/dev/null)" in
  *0.4.1*) ;;
  *) fail "clap-validator 0.4.1 must be on PATH" ;;
esac
[ "$(uname -s)" = "Darwin" ] || fail "this project builds on macOS only; uname -s is $(uname -s)"
[ "$(uname -m)" = "arm64" ] || fail "this project builds on Apple silicon only; uname -m is $(uname -m)"

exit "$failed"
