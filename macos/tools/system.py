"""Safe, confirmation-gated macOS system controls."""
import re
import shutil
import subprocess
from tools.registry import register


def _call(argv, timeout=20):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip() or f'Command failed: {argv[0]}')
    return result.stdout.strip()


@register('lock_pc', 'Lock the Mac session. Confirmation required. arguments={}')
def lock_pc():
    session = '/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession'
    if shutil.which(session):
        _call([session, '-suspend'])
    else:
        _call(['osascript', '-e', 'tell application "System Events" to keystroke "q" using {control down, command down}'])
    return 'Lock requested.'


@register('power_action', 'Sleep, restart, or shut down macOS. Confirmation required. arguments={action}')
def power_action(action):
    action = str(action).lower().strip()
    commands = {
        'sleep': 'tell application "System Events" to sleep',
        'restart': 'tell application "System Events" to restart',
        'shutdown': 'tell application "System Events" to shut down',
    }
    if action not in commands:
        raise ValueError('action must be sleep, restart or shutdown')
    _call(['osascript', '-e', commands[action]], timeout=30)
    return f'{action.capitalize()} requested.'


def _wifi_device():
    output = _call(['networksetup', '-listallhardwareports'])
    blocks = re.split(r'\n\s*\n', output)
    for block in blocks:
        if re.search(r'Hardware Port:\s*(Wi-Fi|AirPort)', block, re.I):
            found = re.search(r'Device:\s*(\S+)', block)
            if found:
                return found.group(1)
    raise RuntimeError('macOS Wi-Fi interface not found.')


@register('set_wifi', 'Enable or disable macOS Wi-Fi. Confirmation required; macOS may require privileges. arguments={enabled}')
def set_wifi(enabled):
    # No sudo/elevation. macOS refuses this without the current user's rights.
    value = enabled if isinstance(enabled, bool) else str(enabled).strip().lower() in {'true', '1', 'on', 'yes', 'enable'}
    desired = 'on' if value else 'off'
    _call(['networksetup', '-setairportpower', _wifi_device(), desired])
    return f'Wi-Fi {desired} requested.'


@register('set_brightness', 'Set Mac internal-display brightness if optional brightness CLI is installed. arguments={percent}')
def set_brightness(percent):
    level = max(0, min(100, int(percent)))
    tool = shutil.which('brightness')
    if not tool:
        raise RuntimeError('Brightness control needs the optional macOS brightness CLI (brew install brightness).')
    _call([tool, str(level / 100)])
    return f'Requested brightness {level}%. External displays may not support this command.'
