import boto3
from moto import mock_aws

from app.services import cloud_storage


def test_local_upload_writes_file_and_lists(tmp_path, monkeypatch):
    monkeypatch.setattr(cloud_storage, "S3_BUCKET_NAME", "")
    monkeypatch.setattr(cloud_storage, "LOCAL_STORAGE_ROOT", tmp_path)

    result = cloud_storage.upload_document(
        file_bytes=b"hello world",
        filename="doc.pdf",
        session_id="session-alpha",
        document_id="doc_abc123",
    )

    assert result["bucket"] == "local"
    assert result["uri"].startswith("file://")

    documents = cloud_storage.list_session_documents("session-alpha")
    assert len(documents) == 1
    assert documents[0]["key"].endswith("doc.pdf")


@mock_aws
def test_s3_upload_dedupes_identical_content(monkeypatch):
    bucket = "rag-test-bucket"
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setattr(cloud_storage, "S3_BUCKET_NAME", bucket)
    cloud_storage.get_s3_client.cache_clear()

    client = boto3.client("s3", region_name=cloud_storage.AWS_REGION)
    client.create_bucket(Bucket=bucket)

    payload = {
        "file_bytes": b"identical bytes",
        "filename": "report.pdf",
        "session_id": "session-alpha",
        "document_id": "doc_deadbeef",
    }

    first = cloud_storage.upload_document(**payload)
    second = cloud_storage.upload_document(**payload)

    assert first["key"] == second["key"]
    assert first["uri"].startswith(f"s3://{bucket}/")

    listed = client.list_objects_v2(Bucket=bucket)
    assert listed["KeyCount"] == 1

    cloud_storage.get_s3_client.cache_clear()
