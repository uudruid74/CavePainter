#!/usr/bin/env bash
# smoke-test.sh — Quick baseline verification of the Cave Painter engine
set -euo pipefail

ENGINE="/home/ekl/Documents/Programming/cave-painter/src/engine.py"
OUTDIR="/home/ekl/Documents/Programming/cave-painter/tests/output"
PASS=0
FAIL=0

mkdir -p "$OUTDIR"

echo "🧪 Cave Painter Smoke Test — $(date)"
echo "───"

run_test() {
    local name="$1"
    local sid="smoke-$(uuidgen | cut -c1-8)"
    local outfile="$sid.png"
    local recipe_file="$OUTDIR/recipe-$sid.json"
    
    # Write recipe inline with correct sid
    cat > "$recipe_file" << ENDRECIPE
$2
ENDRECIPE
    
    # Replace OUTPUT_PLACEHOLDER with actual sid filename
    sed -i "s/OUTPUT_PLACEHOLDER/$outfile/" "$recipe_file"
    
    export GDB_SESSION_ID="$sid"
    export GDB_RECIPE="$recipe_file"
    HOME=/home/ekl timeout 45 gimp --no-interface --batch-interpreter python-fu-eval \
      -b "exec(open('$ENGINE').read())" --quit 2>/dev/null
    
    local output_file="/tmp/gopher-draw/$sid/$outfile"
    if [ -f "$output_file" ]; then
        local size=$(stat -c%s "$output_file")
        if [ "$size" -gt 100 ]; then
            echo "✅ $name — ${size}B"
            PASS=$((PASS + 1))
        else
            echo "❌ $name — too small (${size}B)"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "❌ $name — no output at $output_file"
        FAIL=$((FAIL + 1))
    fi
}

# Test 1: Minimal image (no commands, just background)
run_test "Minimal 100x100" '{"canvas":{"width":100,"height":100,"bg":[0.1,0.2,0.4]},"commands":[],"output":"OUTPUT_PLACEHOLDER"}'

# Test 2: Gradient + text
run_test "Gradient+Text 400x300" '{"canvas":{"width":400,"height":300,"bg":[0.08,0.12,0.25]},"commands":[{"op":"gradient","fg":[0.0,0.5,0.8],"bg":[0.05,0.05,0.18],"style":0},{"op":"text","text":"Cave Painter","x":60,"y":140,"size":36,"r":0.0,"g":1.0,"b":0.8}],"output":"OUTPUT_PLACEHOLDER"}'

# Test 3: Two-layer stack
run_test "Layer stack 200x200" '{"canvas":{"width":200,"height":200,"bg":[0.0,0.0,0.0]},"commands":[{"op":"fill","color":[0.5,0.0,0.0]},{"op":"layer","name":"Mid","opacity":50.0},{"op":"fill","color":[0.0,0.0,0.5]}],"output":"OUTPUT_PLACEHOLDER"}'

echo "───"
echo "🏁 $PASS passed, $FAIL failed"
exit $FAIL
