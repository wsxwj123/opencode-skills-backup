import os
import sys
import platform
import subprocess
import getpass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTO_SYNC_SCRIPT = os.path.join(SCRIPT_DIR, "auto_sync.py")
PYTHON_EXEC = sys.executable

def setup_mac():
    print("🍎 Setting up for macOS...")
    
    # Plist content
    plist_label = "com.opencode.skills.backup"
    user_home = os.path.expanduser("~")
    plist_path = os.path.join(user_home, "Library", "LaunchAgents", f"{plist_label}.plist")
    
    # Logs for launchd
    log_out = os.path.join(os.path.dirname(SCRIPT_DIR), "logs", "launchd.log")
    log_err = os.path.join(os.path.dirname(SCRIPT_DIR), "logs", "launchd.err")
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{plist_label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON_EXEC}</string>
        <string>{AUTO_SYNC_SCRIPT}</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>
</dict>
</plist>
"""
    
    try:
        with open(plist_path, "w") as f:
            f.write(plist_content)
        print(f"📄 Created plist at: {plist_path}")
        
        # Unload existing to update
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        # Load new
        subprocess.run(["launchctl", "load", plist_path], check=True)
        print("✅ LaunchAgent loaded successfully! Backup will run every hour.")
        
    except Exception as e:
        print(f"❌ Error setting up macOS task: {e}")

def setup_windows():
    print("🪟 Setting up for Windows...")
    
    task_name = "OpenCodeSkillsBackup"
    # Use pythonw.exe if available to avoid popup window, else python.exe
    python_w = PYTHON_EXEC.replace("python.exe", "pythonw.exe")
    if not os.path.exists(python_w):
        python_w = PYTHON_EXEC
        
    # Schedule task
    # /SC HOURLY /MO 1 = Every 1 hour
    # /F = Force create (overwrite)
    cmd = [
        "schtasks", "/create",
        "/sc", "HOURLY",
        "/mo", "1",
        "/tn", task_name,
        "/tr", f'"{python_w}" "{AUTO_SYNC_SCRIPT}"',
        "/f"
    ]
    
    try:
        subprocess.run(cmd, check=True, shell=True)
        print(f"✅ Scheduled Task '{task_name}' created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creating scheduled task: {e}")
        print("Try running this script as Administrator.")

if __name__ == "__main__":
    if platform.system() == "Darwin":
        setup_mac()
    elif platform.system() == "Windows":
        setup_windows()
    else:
        print(f"❌ Unsupported OS: {platform.system()}")
