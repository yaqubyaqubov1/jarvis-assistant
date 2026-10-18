import queue
import threading
from config import ENABLE_HUD

class HudOverlay:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.queue = queue.Queue()
        self.started = False

    def start(self):
        if not ENABLE_HUD or self.started:
            return
        self.started = True
        self.state_manager.add_listener(self.queue.put)
        threading.Thread(target=self._run, daemon=True, name="jarvis-hud").start()

    def _run(self):
        try:
            import tkinter as tk
            root = tk.Tk()
            root.title("JARVIS")
            root.attributes("-topmost", True)
            root.overrideredirect(True)
            root.geometry("300x56+30+30")
            frame = tk.Frame(root, padx=12, pady=8)
            frame.pack(fill="both", expand=True)
            label = tk.Label(frame, text="JARVIS • SLEEPING", font=("Segoe UI", 12, "bold"))
            label.pack(anchor="w")
            detail = tk.Label(frame, text="", font=("Segoe UI", 9))
            detail.pack(anchor="w")

            def poll():
                try:
                    while True:
                        snap = self.queue.get_nowait()
                        label.config(text=f"JARVIS • {snap.name}")
                        detail.config(text=snap.detail[:60])
                except queue.Empty:
                    pass
                root.after(100, poll)

            root.after(100, poll)
            root.mainloop()
        except Exception as exc:
            print(f"HUD unavailable: {exc}")
