import urllib.request
import urllib.parse
import urllib.error
import json
import re
from typing import Tuple, Optional

def send_windows_toast(title: str, message: str, icon_path: str = "") -> bool:
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

def send_telegram_alert(bot_token: str, chat_id: str, message: str, parse_mode: Optional[str] = None) -> Tuple[bool, str]:
    if not bot_token or not chat_id:
        return False, "Bot token or Chat ID is missing."
    try:
        clean_token = bot_token.strip()
        clean_chat = chat_id.strip()
        url = f"https://api.telegram.org/bot{clean_token}/sendMessage"

        # Auto-detect HTML if message contains HTML tags and no explicit mode provided
        if parse_mode is None:
            if "<b" in message or "<code>" in message or "</" in message:
                effective_mode = "HTML"
            else:
                effective_mode = "Markdown"
        else:
            effective_mode = parse_mode

        payload_dict = {
            "chat_id": clean_chat,
            "text": message
        }
        if effective_mode:
            payload_dict["parse_mode"] = effective_mode

        payload = json.dumps(payload_dict).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True, "Telegram alert dispatched successfully."
                return False, f"Telegram API returned status {resp.status}."
        except urllib.error.HTTPError as http_err:
            # Fallback: if parse_mode failed (e.g. bad markdown/html), retry without parse_mode
            if http_err.code == 400 and effective_mode:
                fallback_payload = json.dumps({
                    "chat_id": clean_chat,
                    "text": re.sub(r'<[^>]+>', '', message) if effective_mode == "HTML" else message
                }).encode("utf-8")
                fallback_req = urllib.request.Request(url, data=fallback_payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(fallback_req, timeout=5) as fb_resp:
                    if fb_resp.status == 200:
                        return True, "Telegram alert dispatched (fallback plain text)."
            return False, f"Telegram API Error ({http_err.code}): {http_err.reason}"
    except Exception as e:
        print(f"Telegram Notification Warning: {e}")
        return False, str(e)
