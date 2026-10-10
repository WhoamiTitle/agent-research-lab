#!/bin/bash
# The script is called from Makefile.
set -eu -o pipefail

find src tests scripts infra -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
find src tests scripts infra -depth -type d -name '__pycache__' -empty -delete
