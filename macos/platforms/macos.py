"""Native macOS helpers used by desktop tools.

No shell=True, forced process kills, sudo, or raw LLM-provided commands.
"""
import subprocess


def _script(script):
    result = subprocess.run(['osascript', '-e', script], capture_output=True,
                            text=True, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'macOS automation permission denied')
    return result.stdout.strip()


def change_volume(delta):
    current = int(float(_script('output volume of (get volume settings)')))
    target = max(0, min(100, current + int(delta)))
    _script(f'set volume output volume {target}')
    return target


def toggle_mute():
    current = _script('output muted of (get volume settings)').lower() == 'true'
    _script(f'set volume output muted {"false" if current else "true"}')
    return not current


def music_control(action):
    # Music.app only; macOS does not provide a reliable global media API here.
    scripts = {
        'playpause': 'tell application "Music" to playpause',
        'next': 'tell application "Music" to next track',
        'previous': 'tell application "Music" to previous track',
    }
    if action not in scripts:
        raise ValueError('Unsupported media command')
    _script(scripts[action])


def mac_key(key):
    """Map Windows-oriented speech/LLM key names to PyAutoGUI macOS keys."""
    key = str(key).strip().lower()
    return {
        'ctrl': 'command', 'control': 'command', 'cmd': 'command',
        'win': 'command', 'windows': 'command', 'super': 'command',
        'option': 'alt', 'return': 'enter', 'escape': 'esc',
    }.get(key, key)


def idle_seconds():
    try:
        import Quartz
        value = Quartz.CGEventSourceSecondsSinceLastEventType(
            Quartz.kCGEventSourceStateCombinedSessionState,
            Quartz.kCGAnyInputEventType,
        )
        return max(0.0, float(value))
    except Exception:
        return None


def screen_recording_granted():
    try:
        import Quartz
        check = getattr(Quartz, 'CGPreflightScreenCaptureAccess', None)
        return bool(check()) if check is not None else None
    except Exception:
        return None


def accessibility_granted():
    try:
        import Quartz
        check = getattr(Quartz, 'AXIsProcessTrusted', None)
        return bool(check()) if check is not None else None
    except Exception:
        return None


def require_screen_recording():
    if screen_recording_granted() is False:
        raise PermissionError('Allow JARVIS / Terminal in System Settings > Privacy & Security > Screen & System Audio Recording, then relaunch.')


def require_accessibility():
    if accessibility_granted() is False:
        raise PermissionError('Allow JARVIS / Terminal in System Settings > Privacy & Security > Accessibility, then relaunch.')
