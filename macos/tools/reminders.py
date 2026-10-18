from datetime import datetime, timedelta
import re
from tools.registry import register
from memory.database import (
    add_reminder, list_reminders as db_list, cancel_reminder as db_cancel,
    update_reminder_due
)

def parse_when(when):
    text = str(when).strip().lower()
    now = datetime.now()

    m = re.fullmatch(r"in\s+(\d+)\s*(second|seconds|minute|minutes|hour|hours)", text)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        if "second" in unit:
            return now + timedelta(seconds=n)
        if "minute" in unit:
            return now + timedelta(minutes=n)
        return now + timedelta(hours=n)

    # tomorrow at 8 pm / tomorrow 20:00
    m = re.fullmatch(r"tomorrow(?:\s+at)?\s+(.+)", text)
    if m:
        base = parse_when(m.group(1))
        return base.replace(year=now.year, month=now.month, day=now.day) + timedelta(days=1)

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %I:%M %p", "%H:%M", "%I:%M %p"):
        try:
            d = datetime.strptime(text.upper(), fmt)
            if fmt in ("%H:%M", "%I:%M %p"):
                d = d.replace(year=now.year, month=now.month, day=now.day)
                if d <= now:
                    d += timedelta(days=1)
            return d
        except ValueError:
            pass
    raise ValueError("Use '8 PM', '20:00', 'tomorrow at 8 PM', '2026-10-05 15:00', or 'in 30 minutes'.")

@register("set_reminder", "Create reminder. arguments={message,when,recurrence?}; recurrence can be daily/weekly")
def set_reminder(message, when, recurrence=None):
    due = parse_when(when)
    recurrence = str(recurrence).lower() if recurrence else None
    if recurrence not in {None, "daily", "weekly"}:
        raise ValueError("recurrence must be daily or weekly")
    rid = add_reminder(str(message), due.isoformat(timespec="seconds"), recurrence, "reminder")
    return f"Reminder {rid} set for {due.strftime('%B %d at %I:%M %p')}: {message}"

@register("set_timer", "Set a countdown timer. arguments={message?,seconds?,minutes?,hours?}")
def set_timer(message="Timer finished.", seconds=0, minutes=0, hours=0):
    total = int(seconds) + int(minutes) * 60 + int(hours) * 3600
    if total <= 0:
        raise ValueError("Timer duration must be greater than zero.")
    due = datetime.now() + timedelta(seconds=total)
    rid = add_reminder(str(message), due.isoformat(timespec="seconds"), None, "timer")
    return f"Timer {rid} set for {total} seconds."

@register("list_reminders", "List active reminders. arguments={}")
def list_reminders():
    rows = db_list("reminder")
    return "\n".join(
        f"{i}. {m} — {datetime.fromisoformat(d).strftime('%b %d %I:%M %p')}"
        + (f" ({r})" if r else "") for i, m, d, r, kind in rows
    ) or "No active reminders."

@register("list_timers", "List active timers. arguments={}")
def list_timers():
    rows = db_list("timer")
    return "\n".join(f"{i}. {m} — {datetime.fromisoformat(d).strftime('%I:%M:%S %p')}"
                     for i, m, d, r, kind in rows) or "No active timers."

@register("cancel_reminder", "Cancel reminder/timer by id. arguments={reminder_id}")
def cancel_reminder(reminder_id):
    db_cancel(int(reminder_id))
    return f"Cancelled {reminder_id}."

@register("snooze_reminder", "Snooze reminder/timer. arguments={reminder_id,minutes?}")
def snooze_reminder(reminder_id, minutes=10):
    due = datetime.now() + timedelta(minutes=int(minutes))
    update_reminder_due(int(reminder_id), due.isoformat(timespec="seconds"))
    return f"Snoozed {reminder_id} for {minutes} minutes."
