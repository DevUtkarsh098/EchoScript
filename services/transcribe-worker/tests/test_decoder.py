import io
import wave

import av
from worker.main import transcribe  # Loads the actual faster-whisper runtime dependencies.


def test_runtime_decodes_pcm_wav_without_downloading_a_model():
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(16000)
        recording.writeframes(b'\x00\x00' * 1600)
    audio.seek(0)
    with av.open(audio) as container:
        assert sum(frame.samples for frame in container.decode(audio=0)) == 1600
    assert callable(transcribe)
