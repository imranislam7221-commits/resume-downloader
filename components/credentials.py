import os
import sys
import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import Callable, Optional

class CredentialsComponent(ctk.CTkFrame):
    def __init__(self, master, on_change: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(
            master,
            corner_radius=14,
            fg_color=("#111827", "#0d1321"),
            border_width=1,
            border_color="#1e293b",
            **kwargs
        )
        self.on_change = on_change

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            self,
            text="Gmail Address:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e2e8f0"
        ).grid(row=0, column=0, padx=(18, 10), pady=(14, 6), sticky="w")

        self.email_entry = ctk.CTkEntry(
            self,
            placeholder_text="your.name@gmail.com",
            height=36,
            corner_radius=8,
            border_color="#334155"
        )
        self.email_entry.grid(row=0, column=1, padx=(0, 18), pady=(14, 6), sticky="ew")
        self.email_entry.bind("<KeyRelease>", self._trigger_change)

        ctk.CTkLabel(
            self,
            text="App Password:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e2e8f0"
        ).grid(row=0, column=2, padx=(18, 10), pady=(14, 6), sticky="w")

        pwd_container = ctk.CTkFrame(self, fg_color="transparent")
        pwd_container.grid(row=0, column=3, padx=(0, 18), pady=(14, 6), sticky="ew")
        pwd_container.grid_columnconfigure(0, weight=1)

        self.password_entry = ctk.CTkEntry(
            pwd_container,
            placeholder_text="16-character Google App Password",
            show="*",
            height=36,
            corner_radius=8,
            border_color="#334155"
        )
        self.password_entry.grid(row=0, column=0, sticky="ew")
        self.password_entry.bind("<KeyRelease>", self._trigger_change)

        self.btn_toggle_pwd = ctk.CTkButton(
            pwd_container,
            text="👁",
            width=36,
            height=36,
            corner_radius=8,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self.toggle_password_visibility
        )
        self.btn_toggle_pwd.grid(row=0, column=1, padx=(6, 0))

        ctk.CTkLabel(
            self,
            text="Base Directory:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e2e8f0"
        ).grid(row=1, column=0, padx=(18, 10), pady=(6, 14), sticky="w")

        self.dir_entry = ctk.CTkEntry(
            self,
            placeholder_text="Select destination folder on your PC...",
            height=36,
            corner_radius=8,
            border_color="#334155"
        )
        self.dir_entry.grid(row=1, column=1, columnspan=2, padx=(0, 12), pady=(6, 14), sticky="ew")
        self.dir_entry.bind("<KeyRelease>", self._trigger_change)

        dir_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        dir_buttons_frame.grid(row=1, column=3, padx=(0, 18), pady=(6, 14), sticky="ew")

        btn_browse = ctk.CTkButton(
            dir_buttons_frame,
            text="📁 Browse...",
            width=96,
            height=36,
            corner_radius=8,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.browse_directory
        )
        btn_browse.pack(side="left", padx=(0, 6))

        btn_open = ctk.CTkButton(
            dir_buttons_frame,
            text="📂 Open",
            width=76,
            height=36,
            corner_radius=8,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self.open_directory
        )
        btn_open.pack(side="left")

    def _trigger_change(self, event=None):
        if self.on_change:
            self.on_change()

    def toggle_password_visibility(self):
        if self.password_entry.cget("show") == "*":
            self.password_entry.configure(show="")
            self.btn_toggle_pwd.configure(text="🔒")
        else:
            self.password_entry.configure(show="*")
            self.btn_toggle_pwd.configure(text="👁")

    def browse_directory(self):
        curr = self.dir_entry.get().strip() or os.getcwd()
        selected = filedialog.askdirectory(initialdir=curr, title="Select Base Download Directory")
        if selected:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, selected)
            self._trigger_change()

    def open_directory(self):
        target = self.dir_entry.get().strip()
        if not target or not os.path.exists(target):
            messagebox.showwarning("Directory Not Found", "Please choose a valid existing folder first.")
            return
        try:
            if sys.platform == "win32":
                os.startfile(target)
            elif sys.platform == "darwin":
                os.system(f'open "{target}"')
            else:
                os.system(f'xdg-open "{target}"')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")

    def get_data(self):
        return {
            "gmail_address": self.email_entry.get().strip(),
            "app_password": self.password_entry.get().strip(),
            "base_directory": self.dir_entry.get().strip()
        }

    def set_data(self, email: str, password: str, directory: str):
        self.email_entry.delete(0, "end")
        self.email_entry.insert(0, email)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, password)
        self.dir_entry.delete(0, "end")
        self.dir_entry.insert(0, directory)
