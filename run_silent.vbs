Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Imran parsonal\pervez vi mollik\Resume downloader"
WshShell.Run "python app.py", 0, False
Set WshShell = Nothing
