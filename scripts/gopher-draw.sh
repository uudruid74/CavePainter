#!/bin/bash
# gopher-draw — Drive GIMP 3.x headless with session isolation
#
# Usage:
#   gopher-draw /path/to/recipe.json [--session SESSION_ID] [--output out.png]
#
# Recipe format: {"canvas":{"width":800,"height":600,"bg":[0.05,0.1,0.2]},"commands":[...],"output":"out.png"}
#
# Session IDs ensure multiple agents don't collide:
#   export GDB_SESSION_ID="$(uuidgen)"
#   gopher-draw recipe.json
#   # output at /tmp/gopher-draw/$GDB_SESSION_ID/output.png

set -euo pipefail

RECIPE="${1:-}"
SESSION="${GDB_SESSION_ID:-$(uuidgen)}"
ENGINE="/home/ekl/Documents/Programming/cave-painter/src/engine.py"

if [ -z "$RECIPE" ]; then
    echo "Usage: gopher-draw <recipe.json> [--session UUID]"
    echo "       GDB_SESSION_ID=... gopher-draw recipe.json"
    exit 1
fi

if [ ! -f "$RECIPE" ]; then
    echo "ERROR: recipe not found: $RECIPE"
    exit 1
fi

export GDB_SESSION_ID="$SESSION"
export GDB_RECIPE="$RECIPE"
export HOME=/home/ekl

mkdir -p "/tmp/gopher-draw/$SESSION"

# Launch GIMP headless with the engine
exec timeout 45 gimp \
    --no-interface \
    --batch-interpreter python-fu-eval \
    -b "exec(open('$ENGINE').read())" \
    --quit 2>/dev/null
