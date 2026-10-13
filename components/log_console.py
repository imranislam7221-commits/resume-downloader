from datetime import datetime
import customtkinter as ctk

class LogConsoleComponent(ctk.CTkFrame):
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
        self.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=16, pady=(10, 6), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="📊 Real-Time Telemetry & Activity Stream",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        ).grid(row=0, column=0, sticky="w")

        btn_clear = ctk.CTkButton(
            top_bar,
            text="Clear Log",
            width=86,
            height=28,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.clear_logs
        )
        btn_clear.grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word",
            corner_radius=8,
            fg_color=("#070a13", "#070a13"),
            text_color="#cbd5e1",
            border_width=1,
            border_color="#1e293b"
        )
        self.log_textbox.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="nsew")
        self.log_textbox.configure(state="disabled")

    def clear_logs(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level.upper()}] {message}\n"
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", formatted)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
