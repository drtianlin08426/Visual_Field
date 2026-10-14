"""
Entry point for the Driver's-License Visual Field Analyzer (graphical UI).

Launch with::

    python app.py

Requirements: Python 3.8+, and ``tkinter`` (part of the standard library on
Windows and macOS; on Linux install the system package ``python3-tk``).
The other dependencies are listed in ``requirements.txt``.
"""
import os
import sys

if getattr(sys, "frozen", False):
    # PyInstaller bundle: files are unpacked into sys._MEIPASS
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _BASE)
_pkg = os.path.join(_BASE, "visual_field_analyzer")
if os.path.isdir(_pkg) and not getattr(sys, "frozen", False):
    sys.path.insert(0, _pkg)

try:
    from visual_field_analyzer.main import VisualFieldAnalyzerApp
except ImportError:  # fall back to flat layout (bundled build)
    from main import VisualFieldAnalyzerApp

if __name__ == "__main__":
    app = VisualFieldAnalyzerApp()
    app.mainloop()
