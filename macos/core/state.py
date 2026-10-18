from dataclasses import dataclass
import threading
import time


VALID_STATES = {
    "SLEEPING",
    "LISTENING",
    "TRANSCRIBING",
    "THINKING",
    "PLANNING",
    "EXECUTING",
    "VERIFYING",
    "DONE",
    "ERROR",
}


@dataclass
class StateSnapshot:
    name: str
    detail: str
    changed_at: float


class StateManager:
    def __init__(self):
        self._lock = threading.Lock()

        self._snapshot = StateSnapshot(
            "SLEEPING",
            "",
            time.time(),
        )

        self._listeners = []

    def add_listener(self, callback):
        self._listeners.append(callback)

    def set(self, name, detail=""):
        if name not in VALID_STATES:
            name = "ERROR"

        detail = str(detail)

        with self._lock:
            current = self._snapshot

            # Do not repeatedly print the same state.
            if (
                current.name == name
                and current.detail == detail
            ):
                return False

            snapshot = StateSnapshot(
                name,
                detail,
                time.time(),
            )

            self._snapshot = snapshot

        print(
            f"[{name}] {detail}".rstrip()
        )

        for callback in list(
            self._listeners
        ):
            try:
                callback(snapshot)

            except Exception:
                pass

        return True

    def get(self):
        with self._lock:
            return self._snapshot


STATE = StateManager()