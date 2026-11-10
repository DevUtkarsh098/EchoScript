import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

from .subtitles import Segment, to_srt, to_vtt


def normalize_audio(source: Path, destination: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(source), "-ac", "1", "-ar", "16000", str(destination)], check=True, timeout=300)


def transcribe(source: Path, output_dir: Path, language: str = "auto") -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model_name = os.getenv("WHISPER_MODEL", "tiny")
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    with tempfile.TemporaryDirectory(prefix="echoscript-") as temporary:
        normalized = Path(temporary) / "audio.wav"
        normalize_audio(source, normalized)
        model = WhisperModel(model_name, device="cpu", compute_type=compute_type, download_root=os.getenv("WHISPER_CACHE_DIR", "/models"))
        raw_segments, info = model.transcribe(str(normalized), language=None if language == "auto" else language, vad_filter=True, beam_size=5)
        segments = [Segment(item.start, item.end, item.text) for item in raw_segments]
    if not segments:
        raise ValueError("No speech was detected in the recording")
    transcript = " ".join(segment.text.strip() for segment in segments).strip()
    (output_dir / "transcript.txt").write_text(transcript + "\n", encoding="utf-8")
    (output_dir / "subtitles.srt").write_text(to_srt(segments), encoding="utf-8")
    (output_dir / "subtitles.vtt").write_text(to_vtt(segments), encoding="utf-8")
    return {"language": info.language, "duration": info.duration, "segments": len(segments)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Transcribe an EchoScript audio job")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--language", default="auto")
    parser.add_argument("--job-id")
    parser.add_argument("--user-sub")
    arguments = parser.parse_args()
    if arguments.job_id:
        if not arguments.user_sub:
            parser.error("--user-sub is required with --job-id")
        from .cloud_job import run_cloud_job
        run_cloud_job(arguments.job_id, arguments.user_sub, arguments.language)
        return
    if not arguments.input or not arguments.output:
        parser.error("--input and --output are required for local transcription")
    print(json.dumps(transcribe(arguments.input, arguments.output, arguments.language)))


if __name__ == "__main__":
    main()

