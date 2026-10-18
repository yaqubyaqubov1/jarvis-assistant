import logging
import queue
import struct
import threading
import time
from collections import deque

import sounddevice as sd
from PySide6.QtCore import QThread, Signal

from config import MIC_DEVICE
from core.assistant import Assistant, clean_command
from core.cancellation import (
    cancel_current_task,
    cancel_requested,
    task_active,
)
from core.scheduler import ReminderScheduler
from core.session import SESSION
from core.state import STATE
from memory.database import init_database
from skills.loader import load_custom_skills
from ui.sfx import SFX
from voice.speech import listen_from_stream, model as speech_model
from voice.tts import speak
from voice.wakeword import create_detector


# Register all tools.
import memory.tools
import tools.apps
import tools.desktop
import tools.files
import tools.knowledge
import tools.modes
import tools.reminders
import tools.system
import tools.web_tools

try:
    import tools.browser
except ImportError:
    pass


log = logging.getLogger("jarvis.gui")


INTERRUPT_PHRASES = {
    "stop",
    "cancel",
    "cancel that",
    "stop that",
    "stop task",
    "interrupt",
    "interrupt task",
    "never mind",
    "nevermind",
}


class JarvisWorker(QThread):
    state_changed = Signal(str, str)
    user_message = Signal(str)
    jarvis_message = Signal(str)
    system_message = Signal(str)
    ready_changed = Signal(bool)
    microphone_changed = Signal(bool)
    assistant_enabled_changed = Signal(bool)
    sfx_enabled_changed = Signal(bool)
    task_busy_changed = Signal(bool)
    confirmation_requested = Signal(str)
    fatal_error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._stop_event = threading.Event()

        self._assistant_enabled = threading.Event()
        self._assistant_enabled.set()

        self._microphone_enabled = threading.Event()
        self._microphone_enabled.set()

        self._voice_enabled = threading.Event()
        self._voice_enabled.set()

        self._task_busy = threading.Event()

        self._queue = queue.Queue()

        self._confirmation_event = threading.Event()
        self._confirmation_result = False

        self._stream = None
        self._detector = None
        self._scheduler = None
        self._assistant = None

    # =====================================================
    # GUI COMMANDS
    # =====================================================

    def submit_text(self, text):
        text = str(text).strip()

        if not text:
            return

        normalized = text.lower().strip().rstrip(".!?")

        # This method is called directly from the GUI thread, so this
        # cancellation happens immediately even while the worker thread is
        # blocked inside Ollama generation.
        if normalized in INTERRUPT_PHRASES:
            if not self.interrupt_current_task():
                self.system_message.emit("There is no active task to interrupt.")
            return

        self._queue.put(("command", text))

    def interrupt_current_task(self):
        if not self._task_busy.is_set() and not task_active():
            return False

        interrupted = cancel_current_task()

        # If JARVIS is waiting on a confirmation dialog, release that wait
        # as well so cancellation does not sit there for 30 seconds.
        self._confirmation_result = False
        self._confirmation_event.set()

        if interrupted:
            self.system_message.emit("Interrupt requested.")

        return interrupted

    def task_busy(self):
        return self._task_busy.is_set()

    # =====================================================
    # TOGGLES
    # =====================================================

    def set_microphone_enabled(self, enabled):
        if enabled:
            self._microphone_enabled.set()
        else:
            self._microphone_enabled.clear()

        self.microphone_changed.emit(bool(enabled))

    def microphone_enabled(self):
        return self._microphone_enabled.is_set()

    def set_voice_enabled(self, enabled):
        if enabled:
            self._voice_enabled.set()
        else:
            self._voice_enabled.clear()

    def voice_enabled(self):
        return self._voice_enabled.is_set()

    def set_sfx_enabled(self, enabled):
        SFX.set_enabled(enabled)
        self.sfx_enabled_changed.emit(bool(enabled))

        if enabled:
            SFX.play("resume", block=False)

    def sfx_enabled(self):
        return SFX.is_enabled()

    def set_assistant_enabled(self, enabled):
        if enabled:
            self._assistant_enabled.set()
            STATE.set("SLEEPING", "say Jarvis")
            SFX.play("resume", block=False)
        else:
            self.interrupt_current_task()
            self._assistant_enabled.clear()
            SESSION.sleep()
            STATE.set("SLEEPING", "paused")
            SFX.play("pause", block=False)

        self.assistant_enabled_changed.emit(bool(enabled))

    def assistant_enabled(self):
        return self._assistant_enabled.is_set()

    # =====================================================
    # CONFIRMATION
    # =====================================================

    def resolve_confirmation(self, approved):
        self._confirmation_result = bool(approved)
        self._confirmation_event.set()

    # =====================================================
    # SHUTDOWN
    # =====================================================

    def request_stop(self):
        self.interrupt_current_task()
        SFX.play("shutdown", block=False)
        self._stop_event.set()
        self._confirmation_result = False
        self._confirmation_event.set()

    # =====================================================
    # STATE / REMINDERS
    # =====================================================

    def _forward_state(self, snapshot):
        self.state_changed.emit(snapshot.name, snapshot.detail)

    def _enqueue_reminder(self, text):
        self._queue.put(("notification", str(text)))

    # =====================================================
    # AUDIO HELPERS
    # =====================================================

    def _clear_microphone_buffer(self, stream):
        try:
            available = stream.read_available
            if available > 0:
                stream.read(available)
        except Exception:
            pass

    def _play_sfx_safely(self, stream, name, block=True):
        if not SFX.is_enabled():
            return

        try:
            stream.stop()
            SFX.play(name, block=block)
        finally:
            try:
                stream.start()
                self._clear_microphone_buffer(stream)
            except Exception:
                pass

    def _speak_safely(self, stream, text):
        text = str(text).strip()

        if not text or not self._voice_enabled.is_set():
            return

        try:
            stream.stop()
            speak(text)
        finally:
            try:
                stream.start()
                self._clear_microphone_buffer(stream)
            except Exception:
                pass

    # =====================================================
    # TOOL CONFIRMATION
    # =====================================================

    def _confirm(self, stream, tool_name, arguments):
        if cancel_requested():
            return False

        if tool_name == "close_all_apps":
            message = (
                "That may close applications containing unsaved work. "
                "Shall I proceed?"
            )
        elif tool_name == "delete_path":
            message = "That will remove a file or folder. Shall I proceed?"
        elif tool_name == "power_action":
            message = "That is a system power operation. Shall I proceed?"
        else:
            message = f"Confirm {tool_name.replace('_', ' ')}?"

        self._confirmation_result = False
        self._confirmation_event.clear()

        self._play_sfx_safely(stream, "confirm", block=True)
        self.confirmation_requested.emit(message)
        self._speak_safely(stream, message)

        self._confirmation_event.wait(timeout=30)

        if self._stop_event.is_set() or cancel_requested():
            return False

        return self._confirmation_result

    # =====================================================
    # COMMAND EXECUTION
    # =====================================================

    @staticmethod
    def _result_looks_like_error(result):
        text = str(result).lower()
        markers = (
            "failed",
            "error",
            "couldn't",
            "could not",
            "unable to",
            "not found",
            "blocked",
        )
        return any(marker in text for marker in markers)

    def _handle_command(self, stream, assistant, command):
        command = str(command).strip()

        if not command:
            return

        self.user_message.emit(command)
        self._task_busy.set()
        self.task_busy_changed.emit(True)

        try:
            STATE.set("THINKING", "processing request")
            SFX.play("thinking", block=False)

            result = assistant.handle(
                command,
                lambda tool, args: self._confirm(
                    stream,
                    tool,
                    args,
                ),
            )

            result = str(result or "").strip()

            if not result:
                return

            if result == "Cancelled.":
                STATE.set("DONE", "interrupted")
                self._play_sfx_safely(stream, "pause", block=True)
                self.jarvis_message.emit("Cancelled.")
                self._speak_safely(stream, "Cancelled.")
                return

            if self._result_looks_like_error(result):
                STATE.set("ERROR", result[:60])
                self._play_sfx_safely(stream, "error", block=True)
            else:
                STATE.set("DONE", result[:60])
                self._play_sfx_safely(stream, "success", block=True)

            self.jarvis_message.emit(result)
            self._speak_safely(stream, result)

        except Exception as exc:
            log.exception("Command failed")
            STATE.set("ERROR", str(exc))
            result = f"I encountered an error: {exc}"
            self.jarvis_message.emit(result)
            self._play_sfx_safely(stream, "error", block=True)

        finally:
            self._task_busy.clear()
            self.task_busy_changed.emit(False)

    # =====================================================
    # QUEUE
    # =====================================================

    def _handle_queued_items(self, stream, assistant):
        while True:
            try:
                kind, payload = self._queue.get_nowait()
            except queue.Empty:
                break

            if kind == "command":
                if not self._assistant_enabled.is_set():
                    self.system_message.emit(
                        "JARVIS is paused. Start the assistant first."
                    )
                    continue

                self._handle_command(stream, assistant, payload)
                SESSION.sleep()

                if self._detector is not None:
                    self._detector.reset()

                STATE.set("SLEEPING", "say Jarvis")

            elif kind == "notification":
                self.jarvis_message.emit(payload)
                self._play_sfx_safely(stream, "wake", block=True)
                self._speak_safely(stream, payload)

    # =====================================================
    # MAIN THREAD
    # =====================================================

    def run(self):
        try:
            init_database()

            loaded = load_custom_skills()
            if loaded:
                self.system_message.emit(
                    "Loaded skills: " + ", ".join(loaded)
                )

            STATE.add_listener(self._forward_state)

            self._detector = create_detector()
            self._assistant = Assistant()

            STATE.set("THINKING", "loading speech model")
            speech_model()

            self._scheduler = ReminderScheduler(self._enqueue_reminder)
            self._scheduler.start()

            frame_size = self._detector.frame_length
            samplerate = self._detector.sample_rate

            wake_buffer_frames = max(
                1,
                int(0.30 * samplerate / frame_size),
            )

            wake_buffer = deque(maxlen=wake_buffer_frames)

            SFX.play("startup", block=True)

            with sd.RawInputStream(
                samplerate=samplerate,
                blocksize=frame_size,
                channels=1,
                dtype="int16",
                device=MIC_DEVICE,
            ) as stream:
                self._stream = stream

                self.ready_changed.emit(True)
                self.system_message.emit("J.A.R.V.I.S. core online.")
                STATE.set("SLEEPING", "say Jarvis")

                while not self._stop_event.is_set():
                    self._handle_queued_items(stream, self._assistant)

                    if not self._assistant_enabled.is_set():
                        time.sleep(0.05)
                        continue

                    if not self._microphone_enabled.is_set():
                        STATE.set("SLEEPING", "microphone muted")
                        time.sleep(0.05)
                        continue

                    SESSION.sleep()
                    STATE.set("SLEEPING", "say Jarvis")

                    frame, overflowed = stream.read(frame_size)

                    if overflowed:
                        log.warning("Wake-word microphone overflow")

                    frame_bytes = bytes(frame)
                    wake_buffer.append(frame_bytes)

                    samples = struct.unpack_from(
                        f"<{frame_size}h",
                        frame_bytes,
                    )

                    if not self._detector.process(samples):
                        continue

                    SESSION.activate()
                    self._play_sfx_safely(stream, "wake", block=True)

                    wake_preroll = tuple(wake_buffer)
                    wake_buffer.clear()

                    STATE.set("LISTENING", "command")

                    raw_command = listen_from_stream(
                        stream,
                        frame_size,
                        sample_rate=samplerate,
                        max_seconds=15,
                        start_timeout=3.5,
                        silence_timeout=1.15,
                        initial_frames=wake_preroll,
                    )

                    command = clean_command(raw_command)

                    if not command:
                        self.jarvis_message.emit("Yes?")
                        self._speak_safely(stream, "Yes?")
                        STATE.set("LISTENING", "command")

                        command = clean_command(
                            listen_from_stream(
                                stream,
                                frame_size,
                                sample_rate=samplerate,
                                max_seconds=15,
                                start_timeout=5,
                                silence_timeout=1.15,
                            )
                        )

                    if command:
                        self._handle_command(
                            stream,
                            self._assistant,
                            command,
                        )

                    SESSION.sleep()
                    self._detector.reset()
                    wake_buffer.clear()
                    STATE.set("SLEEPING", "say Jarvis")

        except Exception as exc:
            log.exception("JARVIS worker crashed")
            self.fatal_error.emit(str(exc))
            STATE.set("ERROR", str(exc))
            SFX.play("error", block=False)

        finally:
            self._task_busy.clear()
            self.task_busy_changed.emit(False)
            self.ready_changed.emit(False)

            try:
                if self._scheduler is not None:
                    self._scheduler.stop()
            except Exception:
                pass

            try:
                if self._detector is not None:
                    self._detector.delete()
            except Exception:
                pass

            self._stream = None
