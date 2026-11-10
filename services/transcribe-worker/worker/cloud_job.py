import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import boto3

from .main import transcribe


def _key(user_sub: str, job_id: str, filename: str | None = None) -> str:
    base = f"users/{quote(user_sub, safe='')}/jobs/{job_id}"
    return f"{base}/{filename}" if filename else f"{base}/input"


def _update(table, user_sub: str, job_id: str, **values) -> None:
    names = {"#" + key: key for key in values}
    assignments = ", ".join(f"#{key} = :{key}" for key in values)
    table.update_item(
        Key={"user_sub": user_sub, "job_id": job_id},
        UpdateExpression="SET " + assignments,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues={":" + key: value for key, value in values.items()},
    )


def run_cloud_job(job_id: str, user_sub: str, language: str = "auto") -> None:
    region = os.environ["AWS_REGION"]
    input_bucket = os.environ["INPUT_BUCKET"]
    output_bucket = os.environ["OUTPUT_BUCKET"]
    table = boto3.resource("dynamodb", region_name=region).Table(os.environ["DYNAMODB_TABLE"])
    s3 = boto3.client("s3", region_name=region)
    result = table.get_item(Key={"user_sub": user_sub, "job_id": job_id}, ConsistentRead=True)
    job = result.get("Item")
    if not job:
        raise RuntimeError("Transcription job was not found")
    if job.get("status") == "TRANSCRIBED":
        return

    now = datetime.now(timezone.utc).isoformat()
    _update(table, user_sub, job_id, status="RUNNING", started_at=now, updated_at=now)
    try:
        with tempfile.TemporaryDirectory(prefix="echoscript-") as temporary:
            root = Path(temporary)
            source = root / Path(job["filename"]).name
            output_dir = root / "outputs"
            s3.download_file(input_bucket, _key(user_sub, job_id), str(source))
            metadata = transcribe(source, output_dir, language)
            output_names = ("transcript.txt", "subtitles.srt", "subtitles.vtt")
            content_types = {
                "transcript.txt": "text/plain; charset=utf-8",
                "subtitles.srt": "application/x-subrip; charset=utf-8",
                "subtitles.vtt": "text/vtt; charset=utf-8",
            }
            for filename in output_names:
                s3.upload_file(
                    str(output_dir / filename),
                    output_bucket,
                    _key(user_sub, job_id, filename),
                    ExtraArgs={"ContentType": content_types[filename]},
                )
            transcript = (output_dir / "transcript.txt").read_text(encoding="utf-8")
            base = f"/api/jobs/{job_id}/files"
            completed = datetime.now(timezone.utc).isoformat()
            _update(
                table,
                user_sub,
                job_id,
                status="TRANSCRIBED",
                updated_at=completed,
                completed_at=completed,
                duration_seconds=Decimal(str(metadata["duration"])),
                transcript_preview=transcript[:1000],
                outputs={
                    "transcript": f"{base}/transcript.txt",
                    "srt": f"{base}/subtitles.srt",
                    "vtt": f"{base}/subtitles.vtt",
                    "audio": f"/api/jobs/{job_id}/audio",
                    "video": None,
                },
            )
    except Exception:
        failed_at = datetime.now(timezone.utc).isoformat()
        _update(
            table,
            user_sub,
            job_id,
            status="FAILED",
            updated_at=failed_at,
            error_message="Transcription processing failed. Please retry the job.",
        )
        raise
