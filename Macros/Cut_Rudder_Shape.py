# Macros/CutterBuild.py
"""
Light Macro - Rudder Profile Cutter (Step 4)
Cuts stock cavity into foil using profile cutter.
"""
import sys, os

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

# Import and run the heavy module
from cutter import cutter_main

if __name__ == "__main__":
    cutter_main.run()