#!/bin/bash
# gimp-shebang-fix — Patch GIMP 3.x Python-Fu scripts for system Python 3.14
#
# GIMP 3.x ships Python-Fu scripts with:  #!/usr/bin/env python3
# On Arch systems where /usr/bin/python3 points to a different version
# than what GIMP's GObject bindings were compiled against, this breaks.
#
# This script patches all GIMP Python-Fu scripts to use the system python3.14.
#
# Usage:
#   sudo ./scripts/gimp-shebang-fix.sh          # Apply fix
#   sudo ./scripts/gimp-shebang-fix.sh --dry-run  # Preview changes
#   sudo ./scripts/gimp-shebang-fix.sh --undo    # Revert to env python3

set -euo pipefail

GIMP_SCRIPT_DIR="/usr/lib/gimp/3.0"
DRY_RUN=false
UNDO=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --undo) UNDO=true ;;
    esac
done

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: Must run as root (sudo). GIMP scripts are under $GIMP_SCRIPT_DIR"
    exit 1
fi

if [ ! -d "$GIMP_SCRIPT_DIR" ]; then
    echo "ERROR: GIMP script directory not found: $GIMP_SCRIPT_DIR"
    echo "Is GIMP 3.x installed?"
    exit 1
fi

COUNT=0

if $UNDO; then
    echo "Reverting shebangs to '#!/usr/bin/env python3'..."
    while IFS= read -r -d '' f; do
        if head -1 "$f" | grep -q 'python3\.14'; then
            sed -i '1s|#!/usr/bin/python3.14|#!/usr/bin/env python3|' "$f"
            COUNT=$((COUNT + 1))
        fi
    done < <(find "$GIMP_SCRIPT_DIR" -name "*.py" -print0)
    echo "Reverted $COUNT file(s)."
elif $DRY_RUN; then
    echo "DRY RUN — would patch these files:"
    while IFS= read -r -d '' f; do
        if head -1 "$f" | grep -qE '^#!/usr/bin/env python3'; then
            echo "  $f"
            COUNT=$((COUNT + 1))
        fi
    done < <(find "$GIMP_SCRIPT_DIR" -name "*.py" -print0)
    echo "Would patch $COUNT file(s)."
else
    echo "Patching shebangs to '#!/usr/bin/python3.14'..."
    while IFS= read -r -d '' f; do
        if head -1 "$f" | grep -qE '^#!/usr/bin/env python3'; then
            sed -i '1s|#!/usr/bin/env python3|#!/usr/bin/python3.14|' "$f"
            COUNT=$((COUNT + 1))
        fi
    done < <(find "$GIMP_SCRIPT_DIR" -name "*.py" -print0)
    echo "Patched $COUNT file(s)."
fi
