import threading
from datetime import datetime, timedelta
from memory.database import due_reminders, disable_reminder, update_reminder_due

class ReminderScheduler:
    def __init__(self, notify):
        self.notify = notify
        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="jarvis-reminders").start()

    def stop(self):
        self.stop_event.set()

    def _loop(self):
        while not self.stop_event.wait(1):
            now = datetime.now().isoformat(timespec="seconds")
            for rid, message, due, recurrence, kind in due_reminders(now):
                self.notify(f"{'Timer' if kind == 'timer' else 'Reminder'}: {message}")
                if recurrence in {"daily", "weekly"}:
                    delta = timedelta(days=1 if recurrence == "daily" else 7)
                    update_reminder_due(rid, (datetime.fromisoformat(due) + delta).isoformat(timespec="seconds"))
                else:
                    disable_reminder(rid)
