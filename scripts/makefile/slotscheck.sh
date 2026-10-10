#!/bin/bash
# The script is called from Makefile.
set -eu -o pipefail

export PYTHONPATH="src:.${PYTHONPATH:+:$PYTHONPATH}"
exec uv run --locked slotscheck "$@"
