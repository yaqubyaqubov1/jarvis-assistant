"""JARVIS macOS application and window tools.

No arbitrary shell or AppleScript interpolation. Quit requests use
NSRunningApplication. A missing app is never replaced with a web search.
"""
from pathlib import Path
import os
import subprocess
import psutil
from memory.database import resolve_alias
from tools.registry import register

APP_ROOTS = [
    Path('/Applications'),
    Path('/System/Applications'),
    Path.home() / 'Applications',
]
ALIASES = {
    'notepad': 'TextEdit', 'notepad++': 'TextEdit', 'text editor': 'TextEdit',
    'explorer': 'Finder', 'file explorer': 'Finder',
    'calculator': 'Calculator', 'terminal': 'Terminal',
    'task manager': 'Activity Monitor', 'settings': 'System Settings',
    'control panel': 'System Settings', 'chrome': 'Google Chrome',
    'vscode': 'Visual Studio Code', 'vs code': 'Visual Studio Code',
    'edge': 'Microsoft Edge',
}
PROTECTED_APPS = {
    'finder', 'dock', 'systemuiserver', 'windowserver', 'loginwindow',
    'jarvis', 'j.a.r.v.i.s.', 'python', 'python3', 'terminal', 'iterm',
    'iterm2', 'pycharm', 'activity monitor', 'system settings',
}


def _workspace():
    from AppKit import NSWorkspace
    return NSWorkspace.sharedWorkspace()


def _running():
    return list(_workspace().runningApplications())


def _protected_pids():
    ids = {os.getpid()}
    try:
        process = psutil.Process(os.getpid())
        while process:
            ids.add(process.pid)
            process = process.parent()
    except (psutil.Error, OSError):
        pass
    return ids


def _apps():
    """Index installed .app bundles, stopping recursion at each app bundle."""
    found = {}
    for root in APP_ROOTS:
        if not root.is_dir():
            continue
        for base, dirs, _ in os.walk(root, onerror=lambda _exc: None):
            for folder in list(dirs):
                if folder.lower().endswith('.app'):
                    name = folder[:-4]
                    found.setdefault(name.lower(), (name, Path(base) / folder))
                    dirs.remove(folder)
    return found


def _resolve_name(target):
    original = str(target).strip().removesuffix('.app')
    if not original:
        raise ValueError('No application was specified.')
    alias = resolve_alias(original.lower())
    if alias:
        original = str(alias).strip()
    return ALIASES.get(original.lower(), original)


@register('list_applications', 'List installed macOS applications. arguments={query?}')
def list_applications(query=''):
    query = str(query).lower().strip()
    names = sorted((item[0] for item in _apps().values() if query in item[0].lower()), key=str.casefold)
    return '\n'.join(names[:150]) if names else 'No matching installed applications found.'


@register('open_application', 'Open an installed macOS application, not a website. arguments={target}')
def open_application(target):
    name = _resolve_name(target)
    installed = _apps()
    match = installed.get(name.lower())
    if match is None:
        candidates = [entry for key, entry in installed.items() if name.lower() in key]
        if len(candidates) == 1:
            match = candidates[0]
    # 'open -a NAME' can find applications in Spotlight/LaunchServices locations
    # missed by folder scanning, but never falls back to opening a website.
    command = ['open', '-a', str(match[1]) if match else name]
    result = subprocess.run(command, text=True, capture_output=True, timeout=15, check=False)
    if result.returncode:
        return f"I could not find or open the macOS application '{name}': {result.stderr.strip()}"
    return f"Requested macOS to open {name}."


@register('close_application', 'Ask a running macOS app to quit gracefully. Confirmation required. arguments={target}')
def close_application(target):
    name = _resolve_name(target)
    if name.lower() in PROTECTED_APPS:
        return f"I won't close protected application {name}."
    ids = _protected_pids()
    matching = [app for app in _running() if str(app.localizedName() or '').lower() == name.lower()]
    if not matching:
        return f'{name} is not running.'
    count = 0
    for app in matching:
        if int(app.processIdentifier()) in ids or app.localizedName().lower() in PROTECTED_APPS:
            continue
        if app.terminate():
            count += 1
    return f'Asked {count} {name} process(es) to quit.'


@register('close_all_apps', 'Ask ordinary user applications to quit, except JARVIS and protected Mac processes. Confirmation required. arguments={}')
def close_all_apps():
    protected = _protected_pids()
    closed = []
    for app in _running():
        name = str(app.localizedName() or '')
        if not name or name.lower() in PROTECTED_APPS:
            continue
        if int(app.processIdentifier()) in protected:
            continue
        # No forced kills: allow applications to prompt about unsaved changes.
        if app.activationPolicy() != 0:  # regular foreground apps only
            continue
        try:
            if app.terminate():
                closed.append(name)
        except Exception:
            continue
    return f"Requested {len(closed)} app(s) to quit: {', '.join(closed[:20])}" if closed else 'No ordinary applications were closed.'


@register('list_windows', 'List on-screen macOS window titles (Screen Recording permission may be needed). arguments={}')
def list_windows():
    try:
        import Quartz
        windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
        lines = []
        for info in windows or []:
            name = str(info.get('kCGWindowOwnerName', '')).strip()
            title = str(info.get('kCGWindowName', '')).strip()
            if name and title:
                lines.append(f'{name}: {title}')
        return '\n'.join(lines[:150]) if lines else 'No visible window titles available. Check Screen Recording permission.'
    except Exception as exc:
        return f'Window listing unavailable: {exc}'


@register('get_active_window', 'Get the frontmost macOS application; window title may need Screen Recording permission. arguments={}')
def get_active_window():
    try:
        app = _workspace().frontmostApplication()
        if app is None:
            return 'No active application.'
        name = str(app.localizedName() or 'Unknown application')
        try:
            import Quartz
            windows = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID)
            for info in windows or []:
                if int(info.get('kCGWindowOwnerPID', -1)) == int(app.processIdentifier()):
                    title = str(info.get('kCGWindowName', '')).strip()
                    if title:
                        return f'{name}: {title}'
        except Exception:
            pass
        return f'Active application: {name}'
    except Exception as exc:
        return f'Active application unavailable: {exc}'
