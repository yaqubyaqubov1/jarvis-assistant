import time

import numpy as np
import sounddevice as sd

from faster_whisper import (
    WhisperModel,
)

from config import (
    SAMPLE_RATE,
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    LISTEN_MAX_SECONDS,
    LISTEN_START_TIMEOUT,
    SILENCE_TIMEOUT,
    VOICE_THRESHOLD,
)


_model = None


def model():

    global _model

    if _model is None:

        print(
            f"Loading Faster-Whisper "
            f"model: {WHISPER_MODEL}"
        )

        _model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=(
                WHISPER_COMPUTE_TYPE
            ),
        )

    return _model


def transcribe(
    audio,
    sample_rate=SAMPLE_RATE,
):

    if audio.size == 0:
        return ""

    if sample_rate != 16000:
        raise ValueError(
            "Speech recognition expects "
            "16 kHz audio."
        )

    float_audio = (
        audio.astype(np.float32)
        / 32768.0
    )

    segments, _ = (
        model().transcribe(
            float_audio,
            language="en",
            beam_size=4,
            temperature=0,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=(
                "Jarvis. Notepad++. "
                "PyCharm. Visual Studio Code. "
                "Chrome. Spotify. Reminder. "
                "Timer. DuckDuckGo."
            ),
        )
    )

    return " ".join(
        segment.text.strip()
        for segment in segments
    ).strip()


def _to_pcm(frame):

    if isinstance(
        frame,
        (
            bytes,
            bytearray,
            memoryview,
        ),
    ):
        return np.frombuffer(
            frame,
            dtype="<i2",
        ).copy()

    return np.asarray(
        frame,
        dtype=np.int16,
    ).reshape(-1).copy()


def _rms(pcm):

    if pcm.size == 0:
        return 0.0

    normalized = (
        pcm.astype(np.float32)
        / 32768.0
    )

    return float(
        np.sqrt(
            np.mean(
                normalized
                * normalized
            )
        )
    )


def listen_from_stream(
    stream,
    frame_length,
    sample_rate=SAMPLE_RATE,
    max_seconds=LISTEN_MAX_SECONDS,
    start_timeout=LISTEN_START_TIMEOUT,
    silence_timeout=SILENCE_TIMEOUT,
    threshold=VOICE_THRESHOLD,
    initial_frames=(),
):

    frames = []

    started = False
    silence = 0.0

    start = time.monotonic()

    frame_seconds = (
        frame_length
        / sample_rate
    )

    # Only receives a tiny amount of audio
    # around the Jarvis wake word.
    #
    # It is NOT the old multi-second
    # background conversation buffer.
    for frame in initial_frames:

        pcm = _to_pcm(frame)

        frames.append(pcm)

        if _rms(pcm) >= threshold:
            started = True

    while (
        time.monotonic() - start
        < max_seconds
    ):

        raw, overflowed = stream.read(
            frame_length
        )

        if overflowed:
            print(
                "JARVIS: microphone "
                "input overflow."
            )

        pcm = np.frombuffer(
            raw,
            dtype="<i2",
        ).copy()

        rms = _rms(pcm)

        if rms >= threshold:

            started = True
            silence = 0.0

            frames.append(pcm)

        elif started:

            frames.append(pcm)

            silence += frame_seconds

            if (
                silence
                >= silence_timeout
            ):
                break

        elif (
            time.monotonic() - start
            >= start_timeout
        ):
            break

    if (
        not started
        or not frames
    ):
        return ""

    return transcribe(
        np.concatenate(frames),
        sample_rate,
    )


def listen(seconds=6):

    frame_length = 512

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        blocksize=frame_length,
        channels=1,
        dtype="int16",
    ) as stream:

        return listen_from_stream(
            stream,
            frame_length,
            max_seconds=seconds,
            start_timeout=seconds,
        )


def list_microphones():

    devices = sd.query_devices()

    return [
        (
            index,
            device["name"],
        )
        for index, device
        in enumerate(devices)
        if (
            device[
                "max_input_channels"
            ]
            > 0
        )
    ]