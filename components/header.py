import customtkinter as ctk

class HeaderComponent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, fg_color=("#1e293b", "#0f172a"), **kwargs)
        self.grid_columnconfigure(0, weight=1)

        title_container = ctk.CTkFrame(self, fg_color="transparent")
        title_container.grid(row=0, column=0, padx=15, pady=12, sticky="w")

        title_label = ctk.CTkLabel(
            title_container,
            text="⚡ Resume Downloader & Gmail Auto-Sorter",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            title_container,
            text="Automated real-time Gmail inbox watcher with smart keyword routing and system tray background execution",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        sub_label.pack(anchor="w")

        self.status_badge = ctk.CTkLabel(
            self,
            text="● IDLE / STOPPED",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#334155",
            text_color="#cbd5e1",
            corner_radius=8,
            padx=12,
            pady=6
        )
        self.status_badge.grid(row=0, column=1, padx=15, pady=12, sticky="e")

    def set_monitoring_state(self, active: bool):
        if active:
            self.status_badge.configure(
                text="● MONITORING ACTIVE",
                fg_color="#065f46",
                text_color="#34d399"
            )
        else:
            self.status_badge.configure(
                text="● IDLE / STOPPED",
                fg_color="#334155",
                text_color="#cbd5e1"
            )
