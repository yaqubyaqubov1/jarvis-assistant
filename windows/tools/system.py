import subprocess
from tools.registry import register

@register("lock_pc", "Lock Windows. Confirmation required. arguments={}")
def lock_pc():
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], shell=False, check=False)
    return "Computer locked."

@register("power_action", "Shutdown/restart/sleep. Confirmation required. arguments={action}")
def power_action(action):
    action = str(action).lower()
    commands = {
        "shutdown": ["shutdown", "/s", "/t", "10"],
        "restart": ["shutdown", "/r", "/t", "10"],
        "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
    }
    if action not in commands:
        raise ValueError("action must be shutdown, restart, or sleep")
    subprocess.run(commands[action], shell=False, check=False)
    return f"{action.capitalize()} command sent."

@register("set_wifi", "Enable/disable the Windows Wi-Fi interface. May require elevated rights. Confirmation required. arguments={enabled}")
def set_wifi(enabled):
    state = "enabled" if bool(enabled) else "disabled"
    subprocess.run(["netsh", "interface", "set", "interface", "name=Wi-Fi", f"admin={state}"],
                   shell=False, check=False)
    return f"Wi-Fi interface requested {state}."

@register("set_brightness", "Set display brightness percent. arguments={percent}")
def set_brightness(percent):
    import screen_brightness_control as sbc
    value = max(0, min(100, int(percent)))
    sbc.set_brightness(value)
    return f"Brightness set to {value}%."
