RSS Bot — README

Quick start

Prerequisites
- Python 3.8+ installed
- (Recommended) Create and activate the virtualenv from the repo root:
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Run once
- Generate RSS now:
  .\.venv\Scripts\python.exe .\main.py
- Serve the site locally (to view index.html):
  .\.venv\Scripts\python.exe -m http.server 8000
  Open http://localhost:8000/index.html

Windows — Task Scheduler (daily)
- GUI: Task Scheduler > Create Basic Task > Name: Run RSS Bot
  Trigger: Daily, set time (e.g., 09:00)
  Action: Start a program
  Program/script: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
  Add arguments:
    -NoProfile -WindowStyle Hidden -Command "& '\"%USERPROFILE%\\.copilot\\repos\\copilot-worktrees\\rss-bot\\cemrenayir-hub-improved-waffle\\.venv\\Scripts\\python.exe\"' '\"%USERPROFILE%\\.copilot\\repos\\copilot-worktrees\\rss-bot\\cemrenayir-hub-improved-waffle\\main.py\"'"
  Start in: C:\Users\<you>\.copilot\repos\copilot-worktrees\rss-bot\cemrenayir-hub-improved-waffle

- CLI (schtasks) example — edit the paths and time before running in an elevated prompt:
  schtasks /Create /SC DAILY /TN "Run RSS Bot" /TR "\"C:\\Users\\CASPER\\.copilot\\repos\\copilot-worktrees\\rss-bot\\cemrenayir-hub-improved-waffle\\.venv\\Scripts\\python.exe\" \"C:\\Users\\CASPER\\.copilot\\repos\\copilot-worktrees\\rss-bot\\cemrenayir-hub-improved-waffle\\main.py\"" /ST 09:00 /F

Logging on Windows
- Edit the scheduled action to redirect output to a log file, e.g. add: > "C:\path\to\rss.log" 2>&1 to the command.

Linux — systemd (daily)
- Create service file /etc/systemd/system/rss-bot.service (replace paths):

  [Unit]
  Description=Run RSS bot
  After=network.target

  [Service]
  WorkingDirectory=/path/to/repo
  ExecStart=/path/to/repo/.venv/bin/python /path/to/repo/main.py
  Restart=no
  StandardOutput=append:/var/log/rss-bot.log
  StandardError=inherit

- Create timer /etc/systemd/system/rss-bot.timer:

  [Unit]
  Description=Run RSS bot daily

  [Timer]
  OnCalendar=*-*-* 09:00:00
  Persistent=true

  [Install]
  WantedBy=timers.target

- Enable and start:
  sudo systemctl daemon-reload
  sudo systemctl enable --now rss-bot.timer

Notes
- Replace paths with your actual user/repo paths.
- To test manually run the ExecStart command and inspect logs.

Need help: create the Windows scheduled task now (I will run schtasks) or write the systemd unit files for you?