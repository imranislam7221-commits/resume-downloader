# ⚡ Resume Downloader & Gmail Auto-Sorter

A modern, automated Desktop Application built with **CustomTkinter**, **imap_tools**, and **pystray** to automatically monitor Gmail inboxes in real-time, extract resumes (`.pdf`, `.docx`, `.doc`), and sort them into company-specific folders.

---

## 📁 Project Architecture (Modular Structure)

```
Resume downloader/
│
├── components/                  # UI Components (Alada Alada Component)
│   ├── header.py               # Header title, subtitle, and dynamic status badge
│   ├── credentials.py          # Gmail address, App Password, directory picker
│   ├── rules_table.py          # Dynamic company rules grid (Add / Remove rows)
│   ├── log_console.py          # Real-time console activity logger
│   └── __init__.py
│
├── services/                    # Background Services
│   ├── config_manager.py       # Auto-saves and loads config.json
│   ├── email_watcher.py        # Background IMAP thread for monitoring & downloading
│   ├── tray_service.py         # System tray (minimize to tray, context menu)
│   └── __init__.py
│
├── utils/                       # Helper Utilities
│   ├── file_utils.py           # Filename sanitization, duplicate renaming
│   ├── icon_generator.py       # PIL dynamic fallback icon generator
│   └── __init__.py
│
├── app.py                       # Main application entry point
├── config.json                  # Auto-saved user configurations
├── requirements.txt             # Project dependencies
├── run.bat                      # 1-Click launcher for Windows
└── test_suite.py                # Unit test verification suite
```

---

## 🚀 How to Run (Kivabe Run Korben)

### 1. Requirements Install
```bash
pip install -r requirements.txt
```

### 2. App Launch
- Direct double-click on `run.bat`
- Or terminal theke:
```bash
python app.py
```

---

## 🔑 Gmail App Password Setup (Google Setup Guide)

Gmail er standard password ekhane kaj korbe na, Google er security policy onujayi **16-character App Password** proyojon:

1. Apnar Google Account-e jan: [myaccount.google.com](https://myaccount.google.com)
2. **Security** tab-e giye **2-Step Verification** ON koren.
3. Search bar-e likhun **"App passwords"** ba Security theke **App passwords** select koren.
4. App name din (e.g., `Resume Downloader`) ebong **Create** click koren.
5. 16-character er ekta password paben (e.g., `abcd efgh ijkl mnop`).
6. Ei password-ti app-er **App Password** field-e paste korun.

---

## 🛠 Key Features

1. **Modern Dark Theme UI**: Built with CustomTkinter.
2. **Dynamic Company Table**: Joto iccha company name ar keyword/email rule jog ba delete korte parben.
3. **Smart Email Filtering**: Sender email address ebong Subject line check kore correct company detect kore.
4. **Auto Attachment Extraction**: `.pdf`, `.docx`, ebong `.doc` files download kore company folder-e sort kore.
5. **Mark as Read**: Download shesh hole Gmail-e email-ti 'SEEN' mark kore dey jate bar bar process na hoy.
6. **System Tray Integration**: Window 'X' (close) korle app bondho hoy na, background-e system tray-te minimize thake. Tray theke restore ba exit kora jay.
7. **Auto Config Save**: Folder path, email credentials, ar company rules automatic `config.json`-e save hoy.
