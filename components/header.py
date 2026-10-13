import customtkinter as ctk

class HeaderComponent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            corner_radius=14,
            fg_color=("#111827", "#0d1321"),
            border_width=1,
            border_color="#1e293b",
            **kwargs
        )
        self.grid_columnconfigure(0, weight=1)

        title_container = ctk.CTkFrame(self, fg_color="transparent")
        title_container.grid(row=0, column=0, padx=18, pady=14, sticky="w")

        title_label = ctk.CTkLabel(
            title_container,
            text="⚡ ResumeFlow Pro",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#38bdf8"
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            title_container,
            text="Autonomous Gmail candidate intake pipeline & company keyword auto-sorter",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        sub_label.pack(anchor="w")

        self.status_badge = ctk.CTkLabel(
            self,
            text="● ENGINE IDLE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#1e293b",
            text_color="#94a3b8",
            corner_radius=10,
            padx=14,
            pady=7
        )
        self.status_badge.grid(row=0, column=1, padx=18, pady=14, sticky="e")

    def set_monitoring_state(self, active: bool):
        if active:
            self.status_badge.configure(
                text="● MONITORING ACTIVE",
                fg_color="#064e3b",
                text_color="#34d399"
            )
        else:
            self.status_badge.configure(
                text="● ENGINE IDLE",
                fg_color="#1e293b",
                text_color="#94a3b8"
            )
