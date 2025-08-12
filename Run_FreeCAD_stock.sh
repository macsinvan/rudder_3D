# Create AutoRun package (Init.py + InitGui.py) in the user Mod path
AUTORUN_DIR="$HOME/Library/Preferences/FreeCAD/Mod/AutoRun"
mkdir -p "$AUTORUN_DIR"

# Minimal Init.py so FreeCAD sees this as a module
cat > "$AUTORUN_DIR/Init.py" <<'PY'
# AutoRun/Init.py — required so FreeCAD treats this as a module
PY

# InitGui.py that works on 1.0.1 (PySide2) and runs the macro passed via --pass
cat > "$AUTORUN_DIR/InitGui.py" <<'PY'
import sys, os, traceback

# FreeCAD 1.0.x uses PySide2
try:
    from PySide2 import QtCore
except Exception:
    # Fallback just in case
    from PySide import QtCore  # type: ignore

import FreeCADGui

def _run_macro():
    try:
        # Take the first non-option argv (after --pass) as macro path
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

# Normalize line endings (just in case)
perl -pi -e 's/\r$//' "$AUTORUN_DIR/Init.py" "$AUTORUN_DIR/InitGui.py"

# Close FreeCAD so it honors new module on next start
pgrep -x "FreeCAD" >/dev/null && { osascript -e 'tell application "FreeCAD" to quit' || true; sleep 2; killall FreeCAD 2>/dev/null || true; }

# Now launch GUI and pass your macro path via --pass
/Applications/FreeCAD.app/Contents/MacOS/FreeCAD --pass "/Users/andrewmackenzie/Rudder_Code/Macros/import_temp.FCMacro"