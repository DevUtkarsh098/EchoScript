from pathlib import Path
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from .models import Job


def input_object_key(job: Job) -> str:
    return f"users/{quote(job.user_sub, safe='')}/jobs/{job.id}/input"


def output_object_key(job: Job, filename: str) -> str:
    if filename not in {"transcript.txt", "subtitles.srt", "subtitles.vtt"}:
        raise ValueError("Unsupported output filename")
    return f"users/{quote(job.user_sub, safe='')}/jobs/{job.id}/{filename}"


class LocalStorage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def upload_target(self, job: Job, public_api_url: str, expires_in: int) -> tuple[str, dict[str, str]]:
        del expires_in
        return f"{public_api_url}/api/uploads/{job.id}", {"Content-Type": job.content_type}

    def confirm_upload(self, job: Job) -> bool:
        return bool(list((self.data_dir / "uploads" / job.user_sub).glob(f"{job.id}-*")))

    def local_upload_path(self, job: Job) -> Path:
        return self.data_dir / "uploads" / job.user_sub / f"{job.id}-{Path(job.filename).name}"

    def local_output_path(self, job: Job, filename: str) -> Path:
        return self.data_dir / "outputs" / job.user_sub / job.id / filename


class S3Storage:
    def __init__(self, region_name: str, input_bucket: str, output_bucket: str, expires_in: int = 900):
        if not input_bucket or not output_bucket:
            raise ValueError("INPUT_BUCKET and OUTPUT_BUCKET are required for S3 storage")
        self.s3 = boto3.client(
            "s3",
            region_name=region_name,
            endpoint_url=f"https://s3.{region_name}.amazonaws.com",
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )
        self.input_bucket = input_bucket
        self.output_bucket = output_bucket
        self.expires_in = expires_in

    def upload_target(self, job: Job, public_api_url: str = "", expires_in: int | None = None) -> tuple[str, dict[str, str]]:
        del public_api_url
        ttl = expires_in or self.expires_in
        key = input_object_key(job)
        url = self.s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.input_bucket,
                "Key": key,
                "ContentType": job.content_type,
                "ContentLength": job.size_bytes,
            },
            ExpiresIn=ttl,
        )
        return url, {"Content-Type": job.content_type}

    def confirm_upload(self, job: Job) -> bool:
        try:
            response = self.s3.head_object(Bucket=self.input_bucket, Key=input_object_key(job))
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        return response.get("ContentLength") == job.size_bytes and response.get("ContentType", "").lower() == job.content_type.lower()

    def download_url(self, job: Job, filename: str) -> str:
        if filename == "audio":
            bucket, key = self.input_bucket, input_object_key(job)
            content_type = job.content_type
            disposition = "inline"
        else:
            bucket, key = self.output_bucket, output_object_key(job, filename)
            content_type = "text/plain; charset=utf-8" if filename == "transcript.txt" else "text/vtt; charset=utf-8" if filename == "subtitles.vtt" else "application/x-subrip"
            disposition = "attachment"
        download_name = Path(job.filename).name if filename == "audio" else filename
        return self.s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": f"{disposition}; filename*=UTF-8''{quote(download_name, safe='')}",
            },
            ExpiresIn=self.expires_in,
        )


def build_storage(settings):
    if settings.storage_backend.lower() == "s3":
        return S3Storage(settings.aws_region, settings.input_bucket, settings.output_bucket, settings.presigned_url_ttl_seconds)
    if settings.storage_backend.lower() != "local":
        raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")
    return LocalStorage(settings.data_dir)
