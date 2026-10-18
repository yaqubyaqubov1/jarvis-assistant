from core.state import STATE

def sleeping(detail=""):
    STATE.set("SLEEPING", detail)
def listening(detail=""):
    STATE.set("LISTENING", detail)
def transcribing(detail=""):
    STATE.set("TRANSCRIBING", detail)
def thinking(detail=""):
    STATE.set("THINKING", detail)
def planning(detail=""):
    STATE.set("PLANNING", detail)
def executing(detail=""):
    STATE.set("EXECUTING", detail)
def done(detail=""):
    STATE.set("DONE", detail)
def error(detail=""):
    STATE.set("ERROR", detail)
