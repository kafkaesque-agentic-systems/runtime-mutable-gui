#!/bin/sh
# Purpose: the steps of environment setup that need administrator rights or a person.
# The pipeline never runs this file and never uses sudo; the owner runs it once.
# Usage: sh setup-prerequisites.sh        (prints each step and asks before running it)
# Side effects: installs the system packages listed below.
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

# step "<<what this installs and why the project needs it>>" "<<sudo command>>"

echo "Done. Verify with the commands in docs/RUNBOOK.md section 1."
