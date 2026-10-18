from dataclasses import dataclass

@dataclass
class UndoAction:
    tool: str
    arguments: dict
    description: str

class UndoManager:
    def __init__(self, max_items=20):
        self.items = []
        self.max_items = max_items

    def push(self, tool, arguments, description):
        self.items.append(UndoAction(tool, dict(arguments), description))
        self.items = self.items[-self.max_items:]

    def pop(self):
        return self.items.pop() if self.items else None

    def last_description(self):
        return self.items[-1].description if self.items else None

UNDO = UndoManager()
