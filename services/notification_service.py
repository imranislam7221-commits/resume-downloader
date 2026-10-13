import urllib.request
import urllib.parse
import json

def send_windows_toast(title: str, message: str, icon_path: str = ""):
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="Resume Downloader",
            title=title,
            msg=message,
            duration="short",
            icon=icon_path if icon_path else ""
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return True
    except Exception as e:
        print(f"Windows Toast Warning: {e}")
        return False

def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    if not bot_token or not chat_id:
        return False
    try:
        clean_token = bot_token.strip()
        clean_chat = chat_id.strip()
        url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
        payload = json.dumps({
            "chat_id": clean_chat,
            "text": message,
            "parse_mode": "Markdown"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"Telegram Notification Warning: {e}")
        return False
