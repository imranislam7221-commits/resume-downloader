# ⚡ Resume Downloader & Gmail Auto-Sorter (24/7 Autonomous)

A production-grade, fully automated Desktop & Web Application built with **Python**, **CustomTkinter**, **Flask**, **imap_tools**, and **winotify** to automatically monitor Gmail inboxes in real-time, extract applicant resumes (`.pdf`, `.docx`, `.doc`, `.rtf`), and sort them into company-specific folders completely hands-free.

---

## 🌟 Key Capabilities & Features

1. **24/7 Autonomous Background Execution**:
   - Runs continuously in the background checking for unread applicant emails every 10–15 seconds.
   - **Auto-Start on PC Boot**: Starts silently with Windows directly into the system tray without any annoying console window.

2. **In-Dashboard PDF Viewer**:
   - Read downloaded resumes directly inside the Web Dashboard with a single click on **"👁️ Preview"**.
   - No external PDF reader or File Explorer needed!

3. **Real-Time Notifications**:
   - **Windows Desktop Toast**: Native chime sound and bottom-right banner notification whenever a resume is saved.
   - **Telegram Mobile Alerts**: Optional instant push notifications to your phone with applicant details.

4. **Smart Applicant Naming & Deduping**:
   - Automatically detects the applicant's real name from email headers (e.g. `Tanvir_Hasan_Resume.pdf`).
   - Prevents duplicate filename overwriting with smart version suffixes (`_1`, `_2`).

5. **HR Candidate Roster & CSV Manifest Export**:
   - Generates and maintains a live `resumes_manifest.csv` logging every candidate's name, email, company, file size, subject, and path.
   - 1-Click **"📥 Export CSV"** button in the dashboard for spreadsheet reporting.

6. **Dual Interfaces**:
   - **Web Dashboard**: Modern SaaS Dark Mode UI at `http://localhost:5000`.
   - **Desktop GUI**: Native Dark Mode desktop window with system tray minimization (`pystray`).

---

## 📁 Project Architecture (Modular Structure)

```text
Resume downloader/
│
├── components/                  # Desktop GUI Components
│   ├── header.py               # Header title & status badge
│   ├── credentials.py          # Email, masked password, folder picker
│   ├── rules_table.py          # Dynamic company sorting rules grid
│   ├── log_console.py          # Real-time console activity logger
│   └── __init__.py
│
├── services/                    # Autonomous Core Services
│   ├── config_manager.py       # Configuration auto-save and loader
│   ├── email_watcher.py        # Background IMAP watcher & auto-sorter
│   ├── notification_service.py # Windows native toasts & Telegram alerts
│   ├── startup_manager.py      # Windows Startup folder boot integrator
│   ├── tray_service.py         # System tray background execution
│   └── __init__.py
│
├── utils/                       # Utility Helpers
│   ├── file_utils.py           # Filename sanitization & unique naming
│   ├── icon_generator.py       # Dynamic fallback PIL icon generator
│   └── __init__.py
│
├── app.py                       # Main desktop application entry point
├── web_server.py                # Ultra-modern web dashboard server (Port 5000)
├── config.json                  # Auto-saved user settings (excluded in git)
├── config.example.json          # Configuration schema template
├── requirements.txt             # Dependencies
├── run.bat                      # 1-Click Desktop Launcher
├── run_web.bat                  # 1-Click Web Dashboard Launcher
├── run_silent.vbs               # Completely invisible background launcher
└── test_suite.py                # Automated unit verification suite
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
- **Option A (Web Dashboard):** Run `run_web.bat` or `python web_server.py`, then open `http://localhost:5000` in your browser.
- **Option B (Desktop App):** Run `run.bat` or `python app.py`.
- **Option C (Silent 24/7 Background):** Double-click `run_silent.vbs`.

---

## 🔑 Google App Password Setup Guide

Gmail accounts require a **16-character App Password** for secure IMAP access:
1. Visit [myaccount.google.com/security](https://myaccount.google.com/security).
2. Ensure **2-Step Verification** is turned ON.
3. Search for **"App passwords"** in the top search bar.
4. Name your app (e.g. `Resume Downloader`) and click **Create**.
5. Paste the generated 16-character password into the application.

---

## 🧪 Testing & Validation
Run the built-in test suite:
```bash
python test_suite.py
```
All unit tests pass with 100% verification.
