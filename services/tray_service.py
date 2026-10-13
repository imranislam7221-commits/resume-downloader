import sys
import threading
from typing import Callable, Optional
from PIL import Image
import pystray

class TrayService:
    def __init__(
        self,
        icon_image: Image.Image,
        on_restore: Callable[[], None],
        on_toggle_monitor: Callable[[], None],
        on_exit: Callable[[], None],
        is_monitoring_fn: Callable[[], bool]
    ):
        self.icon_image = icon_image
        self.on_restore = on_restore
        self.on_toggle_monitor = on_toggle_monitor
        self.on_exit = on_exit
        self.is_monitoring_fn = is_monitoring_fn
        self.tray_icon: Optional[pystray.Icon] = None
        self.tray_thread: Optional[threading.Thread] = None

    def start(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open App", lambda icon, item: self.on_restore(), default=True),
            pystray.MenuItem(
                "Start Monitoring",
                lambda icon, item: self.on_toggle_monitor(),
                visible=lambda item: not self.is_monitoring_fn()
            ),
            pystray.MenuItem(
                "Stop Monitoring",
                lambda icon, item: self.on_toggle_monitor(),
                visible=lambda item: self.is_monitoring_fn()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Completely", lambda icon, item: self.on_exit())
        )
        self.tray_icon = pystray.Icon("ResumeDownloader", self.icon_image, "Resume Downloader", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def stop(self):
        if self.tray_icon:
            self.tray_icon.stop()
