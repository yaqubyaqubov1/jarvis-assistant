import math
import struct
import threading
import wave
import subprocess
import shutil

from config import DATA_DIR


SAMPLE_RATE = 44100
SFX_DIR = DATA_DIR / "sfx"


def _envelope(
    index,
    total,
    attack=0.05,
    release=0.18,
):
    if total <= 1:
        return 1.0

    position = index / (
        total - 1
    )

    if position < attack:
        return position / max(
            attack,
            0.001,
        )

    if position > 1.0 - release:
        return (
            1.0 - position
        ) / max(
            release,
            0.001,
        )

    return 1.0


def _tone_samples(
    frequency,
    duration,
    volume=0.35,
    end_frequency=None,
    harmonics=(),
):
    count = max(
        1,
        int(
            SAMPLE_RATE
            * duration
        ),
    )

    output = []

    phase = 0.0

    for index in range(
        count
    ):
        progress = index / max(
            count - 1,
            1,
        )

        if end_frequency is None:
            current_frequency = (
                frequency
            )

        else:
            current_frequency = (
                frequency
                + (
                    end_frequency
                    - frequency
                )
                * progress
            )

        phase += (
            2.0
            * math.pi
            * current_frequency
        ) / SAMPLE_RATE

        value = math.sin(
            phase
        )

        for (
            multiple,
            strength,
        ) in harmonics:

            value += (
                strength
                * math.sin(
                    phase
                    * multiple
                )
            )

        value *= _envelope(
            index,
            count,
        )

        value *= volume

        output.append(
            max(
                -1.0,
                min(
                    1.0,
                    value,
                ),
            )
        )

    return output


def _silence(
    duration,
):
    return [
        0.0
    ] * max(
        1,
        int(
            SAMPLE_RATE
            * duration
        ),
    )


def _write_wav(
    path,
    samples,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    pcm = bytearray()

    for sample in samples:
        value = int(
            max(
                -1.0,
                min(
                    1.0,
                    sample,
                ),
            )
            * 32767
        )

        pcm.extend(
            struct.pack(
                "<h",
                value,
            )
        )

    with wave.open(
        str(path),
        "wb",
    ) as wav:

        wav.setnchannels(
            1
        )

        wav.setsampwidth(
            2
        )

        wav.setframerate(
            SAMPLE_RATE
        )

        wav.writeframes(
            bytes(pcm)
        )


def _sequence(
    *parts,
):
    samples = []

    for part in parts:

        if (
            part[0]
            == "silence"
        ):
            samples.extend(
                _silence(
                    part[1]
                )
            )

            continue

        (
            _,
            frequency,
            duration,
            volume,
            end_frequency,
        ) = part

        samples.extend(
            _tone_samples(
                frequency,
                duration,
                volume=volume,
                end_frequency=(
                    end_frequency
                ),
                harmonics=(
                    (
                        2,
                        0.12,
                    ),
                    (
                        3,
                        0.04,
                    ),
                ),
            )
        )

    return samples


def ensure_default_sounds():

    SFX_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    definitions = {

        "startup":
            _sequence(
                (
                    "tone",
                    310,
                    0.12,
                    0.22,
                    420,
                ),
                (
                    "silence",
                    0.035,
                ),
                (
                    "tone",
                    520,
                    0.15,
                    0.24,
                    690,
                ),
                (
                    "silence",
                    0.04,
                ),
                (
                    "tone",
                    760,
                    0.22,
                    0.27,
                    980,
                ),
            ),

        "wake":
            _sequence(
                (
                    "tone",
                    690,
                    0.07,
                    0.24,
                    980,
                ),
                (
                    "silence",
                    0.025,
                ),
                (
                    "tone",
                    1040,
                    0.09,
                    0.22,
                    1280,
                ),
            ),

        "thinking":
            _sequence(
                (
                    "tone",
                    520,
                    0.08,
                    0.14,
                    590,
                ),
                (
                    "silence",
                    0.04,
                ),
                (
                    "tone",
                    620,
                    0.08,
                    0.13,
                    700,
                ),
                (
                    "silence",
                    0.04,
                ),
                (
                    "tone",
                    760,
                    0.08,
                    0.12,
                    840,
                ),
            ),

        "confirm":
            _sequence(
                (
                    "tone",
                    570,
                    0.10,
                    0.20,
                    650,
                ),
                (
                    "silence",
                    0.045,
                ),
                (
                    "tone",
                    820,
                    0.12,
                    0.22,
                    900,
                ),
            ),

        "success":
            _sequence(
                (
                    "tone",
                    620,
                    0.09,
                    0.18,
                    720,
                ),
                (
                    "silence",
                    0.025,
                ),
                (
                    "tone",
                    920,
                    0.14,
                    0.22,
                    1120,
                ),
            ),

        "error":
            _sequence(
                (
                    "tone",
                    410,
                    0.12,
                    0.22,
                    330,
                ),
                (
                    "silence",
                    0.035,
                ),
                (
                    "tone",
                    285,
                    0.18,
                    0.24,
                    220,
                ),
            ),

        "pause":
            _sequence(
                (
                    "tone",
                    680,
                    0.08,
                    0.15,
                    560,
                ),
                (
                    "silence",
                    0.03,
                ),
                (
                    "tone",
                    480,
                    0.12,
                    0.16,
                    390,
                ),
            ),

        "resume":
            _sequence(
                (
                    "tone",
                    390,
                    0.08,
                    0.15,
                    500,
                ),
                (
                    "silence",
                    0.03,
                ),
                (
                    "tone",
                    610,
                    0.12,
                    0.18,
                    760,
                ),
            ),

        "shutdown":
            _sequence(
                (
                    "tone",
                    760,
                    0.10,
                    0.18,
                    620,
                ),
                (
                    "silence",
                    0.035,
                ),
                (
                    "tone",
                    520,
                    0.12,
                    0.17,
                    390,
                ),
                (
                    "silence",
                    0.035,
                ),
                (
                    "tone",
                    330,
                    0.18,
                    0.16,
                    230,
                ),
            ),
    }

    for (
        name,
        samples,
    ) in definitions.items():

        path = (
            SFX_DIR
            / f"{name}.wav"
        )

        if not path.exists():

            _write_wav(
                path,
                samples,
            )


class SoundEffects:

    def __init__(
        self,
    ):
        self.enabled = True

        self._lock = (
            threading.Lock()
        )

        ensure_default_sounds()

    def set_enabled(
        self,
        enabled,
    ):
        self.enabled = bool(
            enabled
        )

        if not self.enabled:
            self.stop()

    def is_enabled(
        self,
    ):
        return self.enabled

    def path(
        self,
        name,
    ):
        return (
            SFX_DIR
            / f"{name}.wav"
        )

    def play(self, name, block=False):
        if not self.enabled:
            return False
        path = self.path(name)
        if not path.exists() or not shutil.which('afplay'):
            return False
        with self._lock:
            self._stop_unlocked()
            try:
                self._process = subprocess.Popen(['afplay', str(path)],
                                                  stdout=subprocess.DEVNULL,
                                                  stderr=subprocess.DEVNULL)
                process = self._process
            except OSError:
                return False
        if block:
            process.wait()
        return True

    def _stop_unlocked(self):
        process = getattr(self, '_process', None)
        if process is not None and process.poll() is None:
            process.terminate()
        self._process = None

    def stop(self):
        with self._lock:
            self._stop_unlocked()


SFX = SoundEffects()