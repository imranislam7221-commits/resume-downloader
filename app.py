import os
import sys
from typing import Optional
from PIL import Image

import customtkinter as ctk
from tkinter import messagebox

from utils.icon_generator import generate_fallback_icon
from services.config_manager import ConfigManager
from services.email_watcher import EmailWatcher
from services.tray_service import TrayService
from services.startup_manager import is_startup_enabled, enable_startup, disable_startup

from components.header import HeaderComponent
from components.credentials import CredentialsComponent
from components.rules_table import RulesTableComponent
from components.log_console import LogConsoleComponent

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
ICON_FILE = os.path.join(APP_DIR, "icon.png")

class ResumeDownloaderApp(ctk.CTk):
    def __init__(self, start_minimized: bool = False):
        super().__init__()

        self.title("ResumeFlow Pro | Autonomous Gmail Ingestion & Applicant Sorter")
        self.geometry("980x800")
        self.minsize(900, 700)

        # Core Services
        self.config_manager = ConfigManager(CONFIG_FILE)
        self.email_watcher: Optional[EmailWatcher] = None
        self.is_monitoring = False

        # Load / Cache Icon
        self.app_icon = self.init_app_icon()

        # Build Modular UI Components
        self.build_ui()

        # Load Saved Config
        self.load_initial_config()

        # Setup System Tray
        self.tray_service = TrayService(
            icon_image=self.app_icon,
            on_restore=self.restore_from_tray,
            on_toggle_monitor=self.toggle_monitoring_from_tray,
            on_exit=self.exit_application,
            is_monitoring_fn=lambda: self.is_monitoring
        )
        self.tray_service.start()

        # Intercept Close Window -> Minimize to Tray
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        self.log_console.log("System initialized. Autonomous engine ready.", "INFO")

        # Auto-start monitoring if configured and credentials exist
        cfg = self.config_manager.load_config()
        if cfg.get("auto_start_monitoring", True) and cfg.get("gmail_address") and cfg.get("app_password"):
            self.after(1000, self.start_monitoring)
            self.log_console.log("Auto-start monitoring activated.", "SUCCESS")

        # Handle start minimized
        if start_minimized:
            self.after(100, self.withdraw)

    def init_app_icon(self) -> Image.Image:
        if os.path.exists(ICON_FILE):
            try:
                return Image.open(ICON_FILE)
            except Exception:
                pass
        icon = generate_fallback_icon()
        try:
            icon.save(ICON_FILE)
        except Exception:
            pass
        return icon

    def build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # 1. Header Component
        self.header = HeaderComponent(self)
        self.header.grid(row=0, column=0, padx=20, pady=(15, 10), sticky="ew")

        # 2. Credentials & Path Component
        self.credentials = CredentialsComponent(self, on_change=self.auto_save_config)
        self.credentials.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # 3. Dynamic Rules Table Component
        self.rules_table = RulesTableComponent(self, on_change=self.auto_save_config)
        self.rules_table.grid(row=2, column=0, padx=20, pady=(10, 0), sticky="nsew")

        # 4. Action / Toggle Button Frame
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.btn_monitor = ctk.CTkButton(
            action_frame,
            text="▶  START ENGINE",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            height=48,
            corner_radius=10,
            fg_color="#10b981",
            hover_color="#059669",
            command=self.toggle_monitoring
        )
        self.btn_monitor.grid(row=0, column=0, sticky="ew")

        # 5. Real-Time Log Console Component
        self.log_console = LogConsoleComponent(self)
        self.log_console.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="nsew")

    def load_initial_config(self):
        cfg = self.config_manager.load_config()
        self.credentials.set_data(
            email=cfg.get("gmail_address", ""),
            password=cfg.get("app_password", ""),
            directory=cfg.get("base_directory", APP_DIR)
        )
        self.rules_table.set_rules(cfg.get("companies", []))

    def auto_save_config(self):
        cred_data = self.credentials.get_data()
        rules = self.rules_table.get_rules()
        existing = self.config_manager.load_config()
        data = {
            **existing,
            **cred_data,
            "poll_interval": 10,
            "companies": rules
        }
        self.config_manager.save_config(data)

    def toggle_monitoring(self):
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        cred = self.credentials.get_data()
        rules = self.rules_table.get_rules()
        cfg = self.config_manager.load_config()

        if not cred["gmail_address"]:
            messagebox.showerror("Missing Input", "Please enter your Gmail address.")
            return
        if not cred["app_password"]:
            messagebox.showerror("Missing Input", "Please enter your 16-character Google App Password.")
            return
        if not cred["base_directory"]:
            messagebox.showerror("Missing Input", "Please select a Base Download Directory.")
            return
        if not os.path.exists(cred["base_directory"]):
            try:
                os.makedirs(cred["base_directory"], exist_ok=True)
            except Exception as e:
                messagebox.showerror("Directory Error", f"Failed to create directory: {e}")
                return
        if not rules:
            messagebox.showerror("Missing Rules", "Please add at least one company filter rule.")
            return

        self.auto_save_config()
        self.is_monitoring = True

        self.header.set_monitoring_state(True)
        self.btn_monitor.configure(
            text="⏹  STOP ENGINE",
            fg_color="#ef4444",
            hover_color="#dc2626"
        )

        # Start watcher service
        self.email_watcher = EmailWatcher(
            email_addr=cred["gmail_address"],
            app_pwd=cred["app_password"],
            base_dir=cred["base_directory"],
            companies=rules,
            create_subfolders=cfg.get("create_subfolders", True),
            prefix_applicant_name=cfg.get("prefix_applicant_name", True),
            log_callback=lambda msg, lvl: self.after(0, lambda: self.log_console.log(msg, lvl)),
            on_error_callback=lambda err: self.after(0, self.stop_monitoring)
        )
        self.email_watcher.start()
        self.log_console.log("Background monitoring loop active. Scanning inbox...", "INFO")

    def stop_monitoring(self):
        self.is_monitoring = False
        if self.email_watcher:
            self.email_watcher.stop()
            self.email_watcher = None

        self.header.set_monitoring_state(False)
        self.btn_monitor.configure(
            text="▶  START ENGINE",
            fg_color="#10b981",
            hover_color="#059669"
        )
        self.log_console.log("Monitoring stopped.", "INFO")

    def toggle_monitoring_from_tray(self):
        self.after(0, self.toggle_monitoring)

    def minimize_to_tray(self):
        self.withdraw()
        self.log_console.log("App minimized to System Tray. Right-click tray icon to open or exit.", "INFO")

    def restore_from_tray(self):
        self.after(0, self._restore_main_window)

    def _restore_main_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def exit_application(self):
        self.after(0, self._cleanup_and_exit)

    def _cleanup_and_exit(self):
        self.stop_monitoring()
        if self.tray_service:
            self.tray_service.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    start_min = "--minimized" in sys.argv
    app = ResumeDownloaderApp(start_minimized=start_min)
    app.mainloop()
