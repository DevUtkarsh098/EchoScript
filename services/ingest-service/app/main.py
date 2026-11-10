from datetime import datetime, timezone
from pathlib import Path
import tempfile
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from .auth import Principal, get_principal
from .config import get_settings
from .dispatcher import SQSJobDispatcher
from .models import CreateJobRequest, CreateJobResponse, Job, JobStatus, VideoStatus
from .processor import process_mock_job, process_mock_video
from .repository import build_repository
from .storage import build_storage

settings = get_settings()
repository = build_repository(settings)
storage = build_storage(settings)
dispatcher = SQSJobDispatcher(settings.job_queue_url, settings.aws_region) if settings.job_queue_url else None
app = FastAPI(title="EchoScript Ingest Service", version=settings.app_version)
app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])

job_submissions = Counter("echoscript_job_submissions_total", "Submitted jobs")
active_jobs = Gauge("echoscript_active_jobs", "Active jobs")
request_duration = Histogram("echoscript_http_request_duration_seconds", "API latency", ["method", "route"])


@app.middleware("http")
async def secure_response(request: Request, call_next):
    with request_duration.labels(request.method, request.url.path).time():
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


def require_job(principal: Principal, job_id: str) -> Job:
    job = repository.get(principal.sub, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/version")
def version() -> dict[str, str]:
    return {"version": settings.app_version, "commit": settings.commit_sha, "color": settings.deployment_color}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/capabilities")
def capabilities() -> dict:
    return {
        "audio_types": ["audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp4"],
        "extensions": ["mp3", "wav", "m4a"],
        "max_upload_bytes": settings.max_upload_bytes,
        "languages": [{"value": "auto", "label": "Auto-detect"}, {"value": "en", "label": "English"}],
        "video": {
            "enabled": settings.mock_video, "mock": settings.mock_video, "max_script_characters": 1500,
            "avatars": [{"id": "demo-nova", "name": "Nova", "role": "Knowledge guide"}, {"id": "demo-mateo", "name": "Mateo", "role": "Business presenter"}, {"id": "demo-aria", "name": "Aria", "role": "Learning coach"}],
            "voices": [{"id": "demo-clear", "name": "Clear & warm"}, {"id": "demo-studio", "name": "Studio neutral"}]
        }
    }


@app.post("/api/jobs", response_model=CreateJobResponse, status_code=201)
def create_job(payload: CreateJobRequest, principal: Principal = Depends(get_principal)) -> CreateJobResponse:
    if payload.size_bytes > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Audio exceeds the configured upload limit")
    if payload.content_type not in {"audio/mpeg", "audio/wav", "audio/x-m4a", "audio/mp4"}:
        raise HTTPException(status_code=422, detail="Unsupported audio type")
    job = Job(id=uuid4().hex, user_sub=principal.sub, **payload.model_dump())
    repository.save(job)
    job_submissions.inc()
    try:
        upload_url, upload_headers = storage.upload_target(job, settings.public_api_url, settings.presigned_url_ttl_seconds)
    except Exception as error:
        job.status = JobStatus.FAILED
        job.error_message = "Could not prepare a secure upload destination."
        job.updated_at = datetime.now(timezone.utc)
        repository.save(job)
        raise HTTPException(status_code=503, detail="Could not prepare an upload destination") from error
    return CreateJobResponse(job=job, upload_url=upload_url, upload_headers=upload_headers)


@app.put("/api/uploads/{job_id}", status_code=204)
async def upload_audio(job_id: str, request: Request, principal: Principal = Depends(get_principal)) -> Response:
    if settings.storage_backend.lower() != "local":
        raise HTTPException(status_code=405, detail="Use the upload URL returned when creating the job")
    job = repository.get(principal.sub, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Upload target not found")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != job.content_type.lower():
        raise HTTPException(status_code=415, detail="Uploaded content type does not match job metadata")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from error
        if declared_size != job.size_bytes:
            raise HTTPException(status_code=400, detail="Uploaded size does not match job metadata")
    upload_dir = storage.local_upload_path(job).parent
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = storage.local_upload_path(job)
    temporary_path: Path | None = None
    received_size = 0
    complete = False
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=upload_dir, prefix=f".{job.id}.", suffix=".uploading", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            async for chunk in request.stream():
                received_size += len(chunk)
                if received_size > job.size_bytes:
                    raise HTTPException(status_code=400, detail="Uploaded size does not match job metadata")
                temporary.write(chunk)
        if received_size != job.size_bytes:
            raise HTTPException(status_code=400, detail="Uploaded size does not match job metadata")
        temporary_path.replace(destination)
        complete = True
    finally:
        if not complete and temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    job.status = JobStatus.UPLOADED
    job.updated_at = datetime.now(timezone.utc)
    repository.save(job)
    return Response(status_code=204)


@app.post("/api/jobs/{job_id}/upload-complete")
def complete_upload(job_id: str, principal: Principal = Depends(get_principal)) -> Job:
    job = require_job(principal, job_id)
    if job.status == JobStatus.UPLOADED:
        return job
    if job.status != JobStatus.CREATED:
        raise HTTPException(status_code=409, detail="Job is not waiting for an upload")
    if not storage.confirm_upload(job):
        raise HTTPException(status_code=409, detail="Uploaded audio is missing or does not match its metadata")
    job.status = JobStatus.UPLOADED
    job.updated_at = datetime.now(timezone.utc)
    repository.save(job)
    return job


@app.post("/api/jobs/{job_id}/start")
def start_job(job_id: str, background: BackgroundTasks, principal: Principal = Depends(get_principal)) -> Job:
    job = require_job(principal, job_id)
    if job.status in {JobStatus.RUNNING, JobStatus.TRANSCRIBED}:
        return job
    if job.status != JobStatus.UPLOADED:
        raise HTTPException(status_code=409, detail="Audio upload must complete before processing")
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    job.updated_at = job.started_at
    repository.save(job)
    if settings.mock_processing:
        active_jobs.inc()
        background.add_task(process_mock_job, repository, settings.data_dir, principal.sub, job.id)
    elif dispatcher:
        try:
            dispatcher.enqueue(job)
        except Exception as error:
            job.status = JobStatus.UPLOADED
            job.error_message = "The processing queue is temporarily unavailable."
            job.updated_at = datetime.now(timezone.utc)
            repository.save(job)
            raise HTTPException(status_code=503, detail="Could not queue the transcription job") from error
    else:
        job.status = JobStatus.UPLOADED
        job.updated_at = datetime.now(timezone.utc)
        repository.save(job)
        raise HTTPException(status_code=503, detail="Job processing is not configured")
    return job


@app.get("/api/jobs")
def list_jobs(status_filter: str | None = Query(default=None, alias="status"), principal: Principal = Depends(get_principal)) -> list[Job]:
    jobs = repository.list(principal.sub)
    return [job for job in jobs if not status_filter or job.status.value == status_filter.upper()]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, principal: Principal = Depends(get_principal)) -> Job:
    return require_job(principal, job_id)


@app.post("/api/jobs/{job_id}/video")
def request_video(job_id: str, background: BackgroundTasks, principal: Principal = Depends(get_principal)) -> Job:
    if not settings.mock_video:
        raise HTTPException(status_code=503, detail="Video generation is not configured")
    job = require_job(principal, job_id)
    if job.status != JobStatus.TRANSCRIBED:
        raise HTTPException(status_code=409, detail="Transcription must complete first")
    if job.video_status in {VideoStatus.PENDING, VideoStatus.RENDERING, VideoStatus.DONE}:
        return job
    job.video_status = VideoStatus.PENDING
    repository.save(job)
    background.add_task(process_mock_video, repository, settings.data_dir, principal.sub, job.id)
    return job


@app.get("/api/jobs/{job_id}/files/{filename}")
def download_file(job_id: str, filename: str, principal: Principal = Depends(get_principal)) -> Response:
    job = require_job(principal, job_id)
    if filename not in {"transcript.txt", "subtitles.srt", "subtitles.vtt", "recap.mp4"}:
        raise HTTPException(status_code=404, detail="File not found")
    if settings.storage_backend.lower() == "s3":
        return RedirectResponse(storage.download_url(job, filename), status_code=307)
    path = storage.local_output_path(job, filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not ready")
    return FileResponse(path, filename=filename)


@app.get("/api/jobs/{job_id}/audio")
def stream_audio(job_id: str, principal: Principal = Depends(get_principal)) -> Response:
    job = require_job(principal, job_id)
    if settings.storage_backend.lower() == "s3":
        return RedirectResponse(storage.download_url(job, "audio"), status_code=307)
    path = storage.local_upload_path(job)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type=job.content_type)

