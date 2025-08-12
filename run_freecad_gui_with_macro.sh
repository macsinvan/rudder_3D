#!/bin/bash
set -euo pipefail

MACRO="/Users/andrewmackenzie/Rudder_Code/Macros/import_temp.FCMacro"
FREECAD_BIN="/Applications/FreeCAD.app/Contents/MacOS/FreeCAD"
AUTORUN_DIR="$HOME/Library/Preferences/FreeCAD/Mod/AutoRun"
INITGUI="$AUTORUN_DIR/InitGui.py"

if [[ ! -f "$MACRO" ]]; then
  echo "❌ Macro not found: $MACRO" >&2
  exit 1
fi
if [[ ! -x "$FREECAD_BIN" ]]; then
  echo "❌ FreeCAD binary not found at: $FREECAD_BIN" >&2
  exit 1
fi

mkdir -p "$AUTORUN_DIR"
cat > "$INITGUI" <<'PY'
import sys, os, traceback
from PySide import QtCore
import FreeCADGui

def _run_macro():
    try:
        args = [a for a in sys.argv if a and not a.startswith('-')]
        if not args:
            print("[AutoRun] No macro path provided via --pass")
            return
        macro = os.path.expanduser(args[0])
        if not os.path.isfile(macro):
            print(f"[AutoRun] Macro not found: {macro}")
            return
        print(f"[AutoRun] Executing macro: {macro}")
        with open(macro, 'r', encoding='utf-8') as f:
            code = f.read()
        g = {'__name__': '__main__'}
        exec(compile(code, macro, 'exec'), g, g)
        print("[AutoRun] Macro finished.")
    except Exception:
        print("[AutoRun] Exception while running macro:")
        traceback.print_exc()

def start():
    try:
        FreeCADGui.showMainWindow()
    except Exception:
        pass
    QtCore.QTimer.singleShot(0, _run_macro)

start()
PY

/usr/bin/perl -pi -e 's/\r$//' "$INITGUI"
echo "✅ AutoRun installed at: $INITGUI"

if pgrep -x "FreeCAD" >/dev/null; then
  echo "🔹 Closing existing FreeCAD…"
  osascript -e 'tell application "FreeCAD" to quit' || true
  sleep 2
  pgrep -x "FreeCAD" >/dev/null && killall FreeCAD || true
fi

echo "▶ Launching FreeCAD GUI with macro:"
echo "   $MACRO"
exec "$FREECAD_BIN" --pass "$MACRO"
