#!/bin/bash
# Cave Painter Test Harness
# Runs all 6 test recipes, reports PASS/FAIL, and verifies session isolation
set -euo pipefail

PROJECT_DIR="/home/ekl/Documents/Programming/cave-painter"
ENGINE="$PROJECT_DIR/src/engine.py"
RECIPES_DIR="$PROJECT_DIR/tests/recipes"
OUTPUT_DIR="$PROJECT_DIR/tests/output"

PASS=0
FAIL=0

mkdir -p "$OUTPUT_DIR"

# ── Helpers ─────────────────────────────────────────────────────────────

red()    { printf '\033[31m%s\033[0m\n' "$1"; }
green()  { printf '\033[32m%s\033[0m\n' "$1"; }
bold()   { printf '\033[1m%s\033[0m\n' "$1"; }

report() {
    local status="$1" label="$2" detail="${3:-}"
    if [ "$status" = "PASS" ]; then
        green "  PASS: $label${detail:+ — $detail}"
        PASS=$((PASS + 1))
    else
        red "  FAIL: $label${detail:+ — $detail}"
        FAIL=$((FAIL + 1))
    fi
}

# ── Run a single recipe ─────────────────────────────────────────────────
# Arguments: recipe_filename (e.g. "01-gradient-sweep.json")
#            label (display name for reporting)
# Returns: 0 on PASS, 1 on FAIL
run_recipe() {
    local recipe="$1"
    local label="${2:-$recipe}"
    local recipe_path="$RECIPES_DIR/$recipe"
    local session_id
    session_id="cp-test-$(uuidgen)"
    local ts
    ts="$(date +%s)"

    # Derive output filename: recipe name without .json + ts + .png
    local base
    base="$(basename "$recipe" .json)"
    local output_name="${base}-${ts}.png"
    local output_path="$OUTPUT_DIR/$output_name"

    if [ ! -f "$recipe_path" ]; then
        report "FAIL" "$label" "recipe not found: $recipe_path"
        return 1
    fi

    # Create a temp recipe with the absolute output path injected
    local tmp_recipe
    tmp_recipe="$(mktemp /tmp/cp-recipe-XXXXXX.json)"
    # Use Python to modify the output field (jq-independent fallback)
    python3 -c "
import json
with open('$recipe_path') as f:
    R = json.load(f)
R['output'] = '$output_path'
with open('$tmp_recipe', 'w') as f:
    json.dump(R, f, indent=2)
"

    # Run GIMP headless via the engine
    export GDB_SESSION_ID="$session_id"
    export GDB_RECIPE="$tmp_recipe"
    export HOME=/home/ekl

    mkdir -p "/tmp/gopher-draw/$session_id"

    if timeout 45 gimp --no-interface --batch-interpreter python-fu-eval \
        -b "exec(open('$ENGINE').read())" --quit 2>/dev/null; then
        if [ -f "$output_path" ] && [ "$(stat -c%s "$output_path")" -gt 1000 ]; then
            local size
            size="$(stat -c%s "$output_path")"
            report "PASS" "$label" "${size} bytes → $output_name"
            rm -f "$tmp_recipe"
            return 0
        else
            local msg="output missing or too small"
            [ -f "$output_path" ] && msg="output only $(stat -c%s "$output_path") bytes"
            report "FAIL" "$label" "$msg"
            rm -f "$tmp_recipe"
            return 1
        fi
    else
        report "FAIL" "$label" "engine exited with error"
        rm -f "$tmp_recipe"
        return 1
    fi
}

# ── Run a recipe in background (for concurrent tests) ───────────────────
run_bg() {
    local recipe="$1"
    local label="$2"
    local session_id
    session_id="cp-test-$(uuidgen)"
    local ts
    ts="$(date +%s)"
    local base
    base="$(basename "$recipe" .json)"
    local output_name="${base}-${ts}.png"
    local output_path="$OUTPUT_DIR/$output_name"

    local tmp_recipe
    tmp_recipe="$(mktemp /tmp/cp-recipe-XXXXXX.json)"

    python3 -c "
import json
with open('$RECIPES_DIR/$recipe') as f:
    R = json.load(f)
R['output'] = '$output_path'
with open('$tmp_recipe', 'w') as f:
    json.dump(R, f, indent=2)
"

    export GDB_SESSION_ID="$session_id"
    export GDB_RECIPE="$tmp_recipe"
    export HOME=/home/ekl

    mkdir -p "/tmp/gopher-draw/$session_id"

    # Run in background, save PID and path for collection
    (
        timeout 45 gimp --no-interface --batch-interpreter python-fu-eval \
            -b "exec(open('$ENGINE').read())" --quit 2>/dev/null
    ) &
    local pid=$!

    # Store info for collection
    echo "$session_id|$pid|$output_path|$label|$tmp_recipe"
}

# ── Collect a background recipe result ──────────────────────────────────
collect_bg() {
    local pid output_path label tmp_recipe
    IFS='|' read -r _ pid output_path label tmp_recipe <<< "$1"

    wait "$pid" 2>/dev/null || true

    if [ -f "$output_path" ] && [ "$(stat -c%s "$output_path")" -gt 1000 ]; then
        local size
        size="$(stat -c%s "$output_path")"
        report "PASS" "$label" "${size} bytes → $(basename "$output_path")"
        rm -f "$tmp_recipe"
        return 0
    else
        local msg="output missing or too small"
        [ -f "$output_path" ] && msg="output only $(stat -c%s "$output_path") bytes"
        report "FAIL" "$label" "$msg"
        rm -f "$tmp_recipe"
        return 1
    fi
}

# ── Tests ───────────────────────────────────────────────────────────────

echo
bold "═══ Cave Painter Test Suite ═══"
echo

# Source the project wrapper if available (as function, skip direct execution)
if [ -f "$PROJECT_DIR/scripts/gopher-draw.sh" ]; then
    # Define the wrapper function manually so we don't trigger the script's arg check
    gopher_draw() {
        python3 -c "import json, sys; exec(open('$ENGINE').read())" "$@"
    }
fi

# Test 1: Gradient Sweep
echo "▸ Test 01: Gradient Sweep — 600x400 linear gradient with label"
run_recipe "01-gradient-sweep.json" "01-gradient-sweep"

# Test 2: Layer Stack
echo "▸ Test 02: Layer Stack — 3 layered fills with varying opacity"
run_recipe "02-layer-stack.json" "02-layer-stack"

# Test 3: Text Variants
echo "▸ Test 03: Text Variants — 3 font sizes on one canvas"
run_recipe "03-text-variants.json" "03-text-variants"

# Test 4: Gradient-Text Combo
echo "▸ Test 04: Gradient-Text Combo — radial gradient + text + emoji"
run_recipe "04-gradient-text-combo.json" "04-gradient-text-combo"

# Test 5 + 6: Session Isolation — run CONCURRENTLY
echo "▸ Test 05/06: Session Isolation — concurrent execution"
echo "   Spawning Session A and Session B in parallel..."

A_INFO=$(run_bg "05-session-isolation.json" "05-session-isolation")
B_INFO=$(run_bg "06-session-isolation-b.json" "06-session-isolation-b")

# Wait for both to finish
eval_A=$(collect_bg "$A_INFO")
eval_B=$(collect_bg "$B_INFO")

# Extract output paths for content comparison
A_OUTPUT=$(echo "$A_INFO" | cut -d'|' -f3)
B_OUTPUT=$(echo "$B_INFO" | cut -d'|' -f3)

# Verify they produced differently-sized (or checksum-different) files
if [ -f "$A_OUTPUT" ] && [ -f "$B_OUTPUT" ]; then
    A_SUM=$(md5sum "$A_OUTPUT" | cut -d' ' -f1)
    B_SUM=$(md5sum "$B_OUTPUT" | cut -d' ' -f1)
    if [ "$A_SUM" != "$B_SUM" ]; then
        report "PASS" "session-isolation-diff" "outputs have different content (unique sessions verified)"
    else
        report "FAIL" "session-isolation-diff" "outputs are identical despite different sessions/recipes"
    fi
else
    if [ ! -f "$A_OUTPUT" ]; then report "FAIL" "session-isolation-A-output" "missing"; fi
    if [ ! -f "$B_OUTPUT" ]; then report "FAIL" "session-isolation-B-output" "missing"; fi
fi

# ── Summary ─────────────────────────────────────────────────────────────
echo
bold "══════════════════════════════"
echo
TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
    green "✓ ALL $TOTAL TESTS PASSED"
else
    red "✗ $FAIL/$TOTAL TESTS FAILED"
fi
echo

exit "$FAIL"
