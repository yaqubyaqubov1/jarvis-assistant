import threading


class TaskCancelled(RuntimeError):
    """Raised when the user interrupts the current JARVIS task."""


_CANCEL_EVENT = threading.Event()
_STATE_LOCK = threading.Lock()
_RESPONSE_LOCK = threading.Lock()
_ACTIVE_TASK = False
_ACTIVE_RESPONSE = None


def begin_task():
    global _ACTIVE_TASK

    with _STATE_LOCK:
        _CANCEL_EVENT.clear()
        _ACTIVE_TASK = True


def finish_task():
    global _ACTIVE_TASK

    with _STATE_LOCK:
        _ACTIVE_TASK = False
        _CANCEL_EVENT.clear()


def task_active():
    with _STATE_LOCK:
        return bool(_ACTIVE_TASK)


def cancel_event():
    return _CANCEL_EVENT


def cancel_requested():
    return _CANCEL_EVENT.is_set()


def checkpoint():
    if _CANCEL_EVENT.is_set():
        raise TaskCancelled("Task cancelled.")


def set_active_response(response):
    global _ACTIVE_RESPONSE

    with _RESPONSE_LOCK:
        _ACTIVE_RESPONSE = response

    if _CANCEL_EVENT.is_set():
        try:
            response.close()
        except Exception:
            pass
        raise TaskCancelled("Task cancelled.")


def clear_active_response(response=None):
    global _ACTIVE_RESPONSE

    with _RESPONSE_LOCK:
        if response is None or _ACTIVE_RESPONSE is response:
            _ACTIVE_RESPONSE = None


def cancel_current_task():
    """
    Interrupt the currently active task.

    The cancellation event stops the planner/executor. If Ollama is
    currently streaming a response, closing the HTTP response also
    interrupts the local generation instead of waiting for it to finish.
    """
    with _STATE_LOCK:
        active = bool(_ACTIVE_TASK)

    if not active:
        return False

    _CANCEL_EVENT.set()

    with _RESPONSE_LOCK:
        response = _ACTIVE_RESPONSE

    if response is not None:
        try:
            response.close()
        except Exception:
            pass

    return True
