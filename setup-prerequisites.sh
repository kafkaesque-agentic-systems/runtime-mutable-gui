#!/bin/sh
# Purpose: the steps of environment setup that need administrator rights or a person.
# The pipeline never runs this file and never uses sudo; the owner runs it once.
# Usage: sh setup-prerequisites.sh        (prints each step and asks before running it)
# Side effects: installs the toolchains and packages listed below (user-level; no step needs sudo today).
set -eu

step() {
  # $1 = what this installs and why, $2 = the command
  printf '\n%s\n  %s\nRun it? [y/N] ' "$1" "$2"
  read -r answer
  case "$answer" in
    y|Y) sh -c "$2" ;;
    *) echo "skipped" ;;
  esac
}

step "the Rust 1.99.1 toolchain with rustfmt and clippy, pinned by rust-toolchain.toml" "rustup toolchain install 1.99.1 --profile minimal --component rustfmt --component clippy"

echo "Done. Verify with the commands in docs/RUNBOOK.md section 1."
