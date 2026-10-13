from datetime import datetime
import customtkinter as ctk

class LogConsoleComponent(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=10, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=12, pady=(8, 4), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="📊 Real-Time Activity Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#cbd5e1"
        ).grid(row=0, column=0, sticky="w")

        btn_clear = ctk.CTkButton(
            top_bar,
            text="Clear Log",
            width=80,
            height=24,
            fg_color="#334155",
            hover_color="#475569",
            command=self.clear_logs
        )
        btn_clear.grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            corner_radius=6,
            fg_color=("#0f172a", "#020617"),
            text_color="#e2e8f0"
        )
        self.log_textbox.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
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
