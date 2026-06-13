from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import boto3
from botocore.client import BaseClient

from core.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
    S3_BUCKET_NAME,
    S3_PREFIX,
)

LOCAL_STORAGE_ROOT = Path(__file__).resolve().parent.parent / "storage" / "sessions"


def sanitize_session_id(session_id: str) -> str:
    """Normalize the incoming session id for remote object paths."""
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in session_id.strip())
    return cleaned or "default"


def _use_local_storage() -> bool:
    return not S3_BUCKET_NAME


def _local_session_dir(session_id: str, document_id: str | None = None) -> Path:
    session_key = sanitize_session_id(session_id)
    base = LOCAL_STORAGE_ROOT / session_key / "uploads"
    if document_id:
        return base / document_id
    return base


def _require_bucket() -> str:
    if not S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME is not configured")
    return S3_BUCKET_NAME


@lru_cache(maxsize=1)
def get_s3_client() -> BaseClient:
    """Create a reusable S3 client using env-configured or instance credentials."""
    client_kwargs: dict[str, Any] = {"service_name": "s3", "region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        client_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
        if AWS_SESSION_TOKEN:
            client_kwargs["aws_session_token"] = AWS_SESSION_TOKEN
    return boto3.client(**client_kwargs)


def build_s3_key(session_id: str, document_id: str, filename: str) -> str:
    session_key = sanitize_session_id(session_id)
    return f"{S3_PREFIX.rstrip('/')}/{session_key}/{document_id}/{filename}"


def upload_document(
    *,
    file_bytes: bytes,
    filename: str,
    session_id: str,
    document_id: str,
    content_type: str | None = None,
) -> dict[str, str]:
    """Upload a document to S3, or to local disk when S3 is not configured."""
    if _use_local_storage():
        doc_dir = _local_session_dir(session_id, document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        file_path = doc_dir / filename
        file_path.write_bytes(file_bytes)
        relative_key = str(file_path.relative_to(LOCAL_STORAGE_ROOT))
        return {
            "bucket": "local",
            "key": relative_key,
            "uri": f"file://{file_path}",
        }

    bucket_name = _require_bucket()
    s3_key = build_s3_key(session_id, document_id, filename)

    extra_args: dict[str, Any] = {
        "Metadata": {
            "session_id": sanitize_session_id(session_id),
            "document_id": document_id,
            "source": filename,
        }
    }
    if content_type:
        extra_args["ContentType"] = content_type

    get_s3_client().put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=file_bytes,
        **extra_args,
    )

    return {
        "bucket": bucket_name,
        "key": s3_key,
        "uri": f"s3://{bucket_name}/{s3_key}",
    }


def list_session_documents(session_id: str) -> list[dict[str, str]]:
    """List uploaded documents for a session from S3 or local storage."""
    if _use_local_storage():
        session_dir = _local_session_dir(session_id)
        if not session_dir.exists():
            return []

        documents: list[dict[str, str]] = []
        for doc_dir in session_dir.iterdir():
            if not doc_dir.is_dir():
                continue
            for file_path in doc_dir.iterdir():
                if file_path.is_file():
                    relative_key = str(file_path.relative_to(LOCAL_STORAGE_ROOT))
                    documents.append({
                        "key": relative_key,
                        "uri": f"file://{file_path}",
                    })
        return documents

    bucket_name = _require_bucket()
    session_key = sanitize_session_id(session_id)
    prefix = f"{S3_PREFIX.rstrip('/')}/{session_key}/"
    response = get_s3_client().list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    contents = response.get("Contents", [])
    return [
        {"key": item["Key"], "uri": f"s3://{bucket_name}/{item['Key']}"}
        for item in contents
        if not item["Key"].endswith("/")
    ]
