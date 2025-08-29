# Macros/OutlineBuildFull.py
"""
Light Macro - Rudder Outline Builder
Calls the heavy module outline_main.py
"""
import sys, os

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

# Import and run the heavy module
from outline import outline_main

if __name__ == "__main__":
    outline_main.run()