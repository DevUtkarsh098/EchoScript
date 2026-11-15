import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .models import JobStatus, VideoStatus
from .metrics import active_jobs, job_results
from .repository import LocalJobRepository


def _stamp(seconds: float, vtt: bool = False) -> str:
    millis = int(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{'.' if vtt else ','}{millis:03}"


def process_mock_video(repository: LocalJobRepository, data_dir: Path, user_sub: str, job_id: str) -> None:
    job = repository.get(user_sub, job_id)
    if not job:
        return
    job.video_status = VideoStatus.RENDERING
    repository.save(job)
    output_dir = data_dir / "outputs" / user_sub / job.id
    output_dir.mkdir(parents=True, exist_ok=True)
    video_path = output_dir / "recap.mp4"
    command = ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x172033:s=1280x720:d=4", "-vf", "drawtext=text='EchoScript AI Recap':fontcolor=white:fontsize=54:x=(w-text_w)/2:y=(h-text_h)/2", "-pix_fmt", "yuv420p", str(video_path)]
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        job = repository.get(user_sub, job_id)
        if job:
            job.video_status = VideoStatus.DONE
            job.outputs.video = f"/api/jobs/{job.id}/files/recap.mp4"
            job.updated_at = datetime.now(timezone.utc)
            repository.save(job)
    except (subprocess.SubprocessError, OSError):
        job = repository.get(user_sub, job_id)
        if job:
            job.video_status = VideoStatus.FAILED
            repository.save(job)


def process_mock_job(repository: LocalJobRepository, data_dir: Path, user_sub: str, job_id: str) -> None:
    job = repository.get(user_sub, job_id)
    if not job:
        return
    active_jobs.inc()
    try:
        time.sleep(1)
        stem = Path(job.filename).stem.replace("_", " ").replace("-", " ")
        transcript = f"This is a local demonstration transcript for {stem}. EchoScript Studio received the audio, processed its speech, and prepared synchronized subtitle files. Enable the faster-whisper worker profile to transcribe the actual recording."
        output_dir = data_dir / "outputs" / user_sub / job.id
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "transcript.txt").write_text(transcript, encoding="utf-8")
        (output_dir / "subtitles.srt").write_text(f"1\n{_stamp(0)} --> {_stamp(8)}\n{transcript}\n", encoding="utf-8")
        (output_dir / "subtitles.vtt").write_text(f"WEBVTT\n\n{_stamp(0, True)} --> {_stamp(8, True)}\n{transcript}\n", encoding="utf-8")
        base = f"/api/jobs/{job.id}/files"
        job.outputs.transcript = f"{base}/transcript.txt"
        job.outputs.srt = f"{base}/subtitles.srt"
        job.outputs.vtt = f"{base}/subtitles.vtt"
        job.outputs.audio = f"/api/jobs/{job.id}/audio"
        job.transcript_preview = transcript
        job.status = JobStatus.TRANSCRIBED
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = job.completed_at
        repository.save(job)
        job_results.labels(status="transcribed").inc()
        if job.generate_video:
            process_mock_video(repository, data_dir, user_sub, job_id)
    except Exception:
        job.status = JobStatus.FAILED
        job.error_message = "The local processor could not complete this job."
        job.updated_at = datetime.now(timezone.utc)
        repository.save(job)
        job_results.labels(status="failed").inc()
    finally:
        active_jobs.dec()

