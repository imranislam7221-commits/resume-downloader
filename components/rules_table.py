import customtkinter as ctk
from typing import List, Dict, Callable, Optional, Any

class RulesTableComponent(ctk.CTkFrame):
    def __init__(self, master, on_change: Optional[Callable[[], None]] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_change = on_change
        self.company_rows: List[Dict[str, Any]] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="📋 Dynamic Company Sorting Rules",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#cbd5e1"
        ).grid(row=0, column=0, sticky="w")

        btn_add = ctk.CTkButton(
            top_bar,
            text="+ Add Company Rule",
            width=150,
            height=30,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda: self.add_rule("", "")
        )
        btn_add.grid(row=0, column=1, sticky="e")

        self.scrollable = ctk.CTkScrollableFrame(
            self,
            height=160,
            corner_radius=8,
            fg_color=("#1e293b", "#111827")
        )
        self.scrollable.grid(row=1, column=0, sticky="nsew")
        self.scrollable.grid_columnconfigure(0, weight=2)
        self.scrollable.grid_columnconfigure(1, weight=3)
        self.scrollable.grid_columnconfigure(2, weight=0)

        self._render_headers()

    def _render_headers(self):
        header_row = ctk.CTkFrame(self.scrollable, fg_color="transparent")
        header_row.pack(fill="x", padx=5, pady=(2, 6))
        header_row.grid_columnconfigure(0, weight=2)
        header_row.grid_columnconfigure(1, weight=3)
        header_row.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(
            header_row,
            text="Company / Subfolder Name",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            anchor="w"
        ).grid(row=0, column=0, padx=(5, 10), sticky="w")

        ctk.CTkLabel(
            header_row,
            text="Filter Keyword / Sender Email (e.g. hr@company.com)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            anchor="w"
        ).grid(row=0, column=1, padx=(5, 10), sticky="w")

        ctk.CTkLabel(
            header_row,
            text="Action",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8",
            width=60
        ).grid(row=0, column=2, padx=(5, 5))

    def add_rule(self, company_name: str = "", filter_keyword: str = ""):
        row_frame = ctk.CTkFrame(self.scrollable, fg_color=("#1e293b", "#1e293b"), corner_radius=6)
        row_frame.pack(fill="x", padx=5, pady=3)
        row_frame.grid_columnconfigure(0, weight=2)
        row_frame.grid_columnconfigure(1, weight=3)
        row_frame.grid_columnconfigure(2, weight=0)

        name_entry = ctk.CTkEntry(row_frame, placeholder_text="e.g. Google", height=32)
        name_entry.insert(0, company_name)
        name_entry.grid(row=0, column=0, padx=(5, 10), pady=4, sticky="ew")
        name_entry.bind("<KeyRelease>", self._trigger_change)

        keyword_entry = ctk.CTkEntry(row_frame, placeholder_text="e.g. hr@google.com or Google Recruitment", height=32)
        keyword_entry.insert(0, filter_keyword)
        keyword_entry.grid(row=0, column=1, padx=(0, 10), pady=4, sticky="ew")
        keyword_entry.bind("<KeyRelease>", self._trigger_change)

        delete_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=36,
            height=32,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        delete_btn.grid(row=0, column=2, padx=(0, 5), pady=4)

        row_data = {
            "frame": row_frame,
            "name_entry": name_entry,
            "keyword_entry": keyword_entry,
            "delete_btn": delete_btn
        }
        delete_btn.configure(command=lambda: self.remove_rule(row_data))
        self.company_rows.append(row_data)
        self._trigger_change()

    def remove_rule(self, row_data: Dict[str, Any]):
        if row_data in self.company_rows:
            self.company_rows.remove(row_data)
            row_data["frame"].destroy()
            self._trigger_change()

    def _trigger_change(self, event=None):
        if self.on_change:
            self.on_change()

    def get_rules(self) -> List[Dict[str, str]]:
        rules = []
        for row in self.company_rows:
            name = row["name_entry"].get().strip()
            kw = row["keyword_entry"].get().strip()
            if name or kw:
                rules.append({"name": name, "keyword": kw})
        return rules

    def set_rules(self, rules: List[Dict[str, str]]):
        for row in list(self.company_rows):
            row["frame"].destroy()
        self.company_rows.clear()
        for r in rules:
            self.add_rule(r.get("name", ""), r.get("keyword", ""))
