# PyInstaller runtime hook: initialize COM for all threads on Windows
import sys

if sys.platform == "win32":
    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        pass
