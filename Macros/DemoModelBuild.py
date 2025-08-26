# Macros/DemoModelBuild.py
"""
Light Macro - Demo Model Generator (Step 5A)
Creates scaled-down demo model with breakaway connections.
"""
import sys, os

# Add project root so Python finds our modules
project = os.path.expanduser("~/Rudder_Code")
sys.path.insert(0, project)

# Import and run the heavy module
from demo import demo_main

if __name__ == "__main__":
    demo_main.run()