import json
import re

import numpy as np

from vosk import (
    Model,
    KaldiRecognizer,
    SetLogLevel,
)

from config import (
    WAKE_MODEL_DIR,
    WAKE_WORD,
    SAMPLE_RATE,
)


SetLogLevel(-1)


class JarvisDetector:

    def __init__(self):

        if not WAKE_MODEL_DIR.exists():
            raise FileNotFoundError(
                f"Vosk model not found: "
                f"{WAKE_MODEL_DIR}"
            )

        print(
            "Loading offline Jarvis "
            "wake detector..."
        )

        self.sample_rate = SAMPLE_RATE
        self.frame_length = 512

        self.model = Model(
            str(WAKE_MODEL_DIR)
        )

        self.candidate_hits = 0

        self._reset()

        print(
            "Jarvis wake detector ready."
        )

    def _reset(self):

        # Do NOT restrict Vosk to only the
        # word "jarvis".
        #
        # A tiny restricted grammar can
        # incorrectly force unrelated speech
        # into the wake word.
        self.recognizer = (
            KaldiRecognizer(
                self.model,
                self.sample_rate,
            )
        )

        self.recognizer.SetWords(True)

        self.candidate_hits = 0

    def process(self, samples):
        """
        Return True only when Jarvis
        is actually detected.
        """

        audio = np.asarray(
            samples,
            dtype=np.int16,
        ).tobytes()

        finished = (
            self.recognizer
            .AcceptWaveform(audio)
        )

        wake_word = (
            WAKE_WORD
            .lower()
            .strip()
        )

        # ---------------------------------
        # COMPLETED RECOGNITION
        # ---------------------------------

        if finished:

            result = json.loads(
                self.recognizer.Result()
            )

            text = (
                result
                .get("text", "")
                .lower()
                .strip()
            )

            detected = bool(
                re.match(
                    rf"^(?:hey\s+)?"
                    rf"{re.escape(wake_word)}"
                    rf"(?:\b|$)",
                    text,
                )
            )

            self._reset()

            if detected:

                print(
                    "Wake word detected: "
                    "Jarvis"
                )

                return True

            return False

        # ---------------------------------
        # PARTIAL RECOGNITION
        # ---------------------------------

        partial_result = json.loads(
            self.recognizer
            .PartialResult()
        )

        partial = (
            partial_result
            .get("partial", "")
            .lower()
            .strip()
        )

        detected_partial = bool(
            re.match(
                rf"^(?:hey\s+)?"
                rf"{re.escape(wake_word)}"
                rf"(?:\b|$)",
                partial,
            )
        )

        if detected_partial:

            self.candidate_hits += 1

            # Require recognition across
            # multiple audio frames to
            # reduce false activations.
            if self.candidate_hits >= 2:

                print(
                    "Wake word detected: "
                    "Jarvis"
                )

                self._reset()

                return True

        else:
            self.candidate_hits = 0

        return False

    def reset(self):
        self._reset()

    def delete(self):
        pass


def create_detector():
    return JarvisDetector()