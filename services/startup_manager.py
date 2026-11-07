import os
import sys

def get_startup_folder() -> str:
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        return os.path.join(appdata, r"Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.expanduser(r"~\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")

STARTUP_FILE_NAME = "ResumeDownloader_AutoStart.vbs"

def is_startup_enabled() -> bool:
    target = os.path.join(get_startup_folder(), STARTUP_FILE_NAME)
    return os.path.exists(target)

def enable_startup(app_dir: str = "") -> bool:
    if not app_dir:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    startup_dir = get_startup_folder()
    os.makedirs(startup_dir, exist_ok=True)
    target = os.path.join(startup_dir, STARTUP_FILE_NAME)

    python_exe = sys.executable
    pythonw_candidate = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    if os.path.exists(pythonw_candidate):
        exec_path = pythonw_candidate
    else:
        exec_path = python_exe

    safe_app_dir = app_dir.replace('"', '""')
    safe_exec = exec_path.replace('"', '""')

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{safe_app_dir}"
WshShell.Run """{safe_exec}"" app.py --minimized", 0, False
Set WshShell = Nothing
'''
    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        return True
    except Exception as e:
        print(f"Failed to enable startup: {e}")
        return False

def disable_startup() -> bool:
    target = os.path.join(get_startup_folder(), STARTUP_FILE_NAME)
    try:
        if os.path.exists(target):
            os.remove(target)
        return True
    except Exception as e:
        print(f"Failed to disable startup: {e}")
        return False
