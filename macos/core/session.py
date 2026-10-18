import time
from config import ENABLE_FOLLOWUP_SESSION, SESSION_TIMEOUT_SECONDS

class ConversationSession:
    def __init__(self):
        self.active_until = 0.0
        self.history = []

    def activate(self):
        self.active_until = time.monotonic() + SESSION_TIMEOUT_SECONDS

    def touch(self):
        if ENABLE_FOLLOWUP_SESSION:
            self.activate()

    def is_active(self):
        return ENABLE_FOLLOWUP_SESSION and time.monotonic() < self.active_until

    def sleep(self):
        self.active_until = 0.0

    def add(self, role, content):
        self.history.append({"role": role, "content": str(content)})
        self.history = self.history[-12:]

SESSION = ConversationSession()
