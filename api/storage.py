"""Where finished films live: local disk (default, served by FastAPI) or Cloudflare R2 (S3-compatible)."""
from __future__ import annotations

from pathlib import Path

from .config import settings
from .jobs import Job


def publish(job: Job, path: Path, content_type: str = "video/mp4") -> str:
    if settings.storage_backend == "r2" and settings.r2_bucket:
        import boto3  # optional dependency: pip install boto3

        s3 = boto3.client(
            "s3", endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key, aws_secret_access_key=settings.r2_secret_key, region_name="auto")
        key = f"films/{job.id}/{path.name}"
        s3.upload_file(str(path), settings.r2_bucket, key, ExtraArgs={"ContentType": content_type})
        return f"{settings.r2_public_url}/{key}"
    return job.url(path)
