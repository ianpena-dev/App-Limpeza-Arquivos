import subprocess
import os
import sys
import datetime

TASK_NAME_PREFIX = "ClearFiles_"

def run_command(cmd):
    """
    Executes a shell command without showing a window.
    """
    try:
        # 0x08000000 is CREATE_NO_WINDOW, which prevents the CMD window from flashing on Windows
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=0x08000000)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def remove_all_tasks():
    """
    Removes all tasks previously created by ClearFiles.
    """
    tasks = ["OnLogon", "Interval", "Shutdown"]
    for t in tasks:
        run_command(["schtasks", "/delete", "/tn", f"{TASK_NAME_PREFIX}{t}", "/f"])

def set_manual_mode():
    """
    Stops all automated cleaning tasks.
    """
    remove_all_tasks()

def set_logon_mode(exe_path):
    """
    Configures a task to run whenever the user logs in.
    """
    remove_all_tasks()
    cmd = ["schtasks", "/create", "/tn", f"{TASK_NAME_PREFIX}OnLogon", 
           "/tr", f'"{exe_path}" --silent', "/sc", "ONLOGON", "/rl", "HIGHEST", "/f"]
    return run_command(cmd)

def set_interval_mode(exe_path, minutes):
    """
    Configures a task to run every X minutes.
    """
    remove_all_tasks()
    cmd = ["schtasks", "/create", "/tn", f"{TASK_NAME_PREFIX}Interval", 
           "/tr", f'"{exe_path}" --silent', "/sc", "MINUTE", "/mo", str(minutes), "/rl", "HIGHEST", "/f"]
    return run_command(cmd)

def set_shutdown_mode(exe_path):
    """
    Configures a task to run when a system shutdown event is detected.
    """
    remove_all_tasks()
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Date>{current_date}</Date>
    <Author>ClearFiles</Author>
  </RegistrationInfo>
  <Triggers>
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="System"&gt;&lt;Select Path="System"&gt;*[System[EventID=1074]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{exe_path}"</Command>
      <Arguments>--silent</Arguments>
    </Exec>
  </Actions>
</Task>
"""
    xml_path = os.path.join(os.environ.get("TEMP", "."), "shutdown_task.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml_content)
    
    cmd = ["schtasks", "/create", "/xml", xml_path, "/tn", f"{TASK_NAME_PREFIX}Shutdown", "/f"]
    success, msg = run_command(cmd)
    
    if os.path.exists(xml_path):
        os.remove(xml_path)
        
    return success, msg
