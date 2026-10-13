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
        # Default to project root directory
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    startup_dir = get_startup_folder()
    os.makedirs(startup_dir, exist_ok=True)
    target = os.path.join(startup_dir, STARTUP_FILE_NAME)

    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{app_dir}"
WshShell.Run "python app.py --minimized", 0, False
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
