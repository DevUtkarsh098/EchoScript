from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.models import Job, JobStatus
from app.repository import DynamoJobRepository
from app.storage import S3Storage, input_object_key


def sample_job() -> Job:
    return Job(
        id="job-123",
        user_sub="user/sub",
        filename='lecture "one".mp3',
        content_type="audio/mpeg",
        size_bytes=123,
        status=JobStatus.CREATED,
        created_at=datetime.now(timezone.utc),
    )


@patch("app.storage.boto3.client")
def test_s3_upload_url_is_scoped_and_binds_content_type(mock_client):
    storage = S3Storage("us-west-2", "input-bucket", "output-bucket")
    url, headers = storage.upload_target(sample_job())

    client_kwargs = mock_client.call_args.kwargs
    assert client_kwargs["region_name"] == "us-west-2"
    assert client_kwargs["endpoint_url"] == "https://s3.us-west-2.amazonaws.com"
    assert client_kwargs["config"].signature_version == "s3v4"
    assert client_kwargs["config"].s3 == {"addressing_style": "virtual"}
    assert url == mock_client.return_value.generate_presigned_url.return_value
    assert headers == {"Content-Type": "audio/mpeg"}
    params = mock_client.return_value.generate_presigned_url.call_args.kwargs
    assert mock_client.return_value.generate_presigned_url.call_args.args[0] == "put_object"
    assert params["Params"] == {
        "Bucket": "input-bucket",
        "Key": "users/user%2Fsub/jobs/job-123/input",
        "ContentType": "audio/mpeg",
        "ContentLength": 123,
    }


@patch("app.storage.boto3.client")
def test_s3_upload_confirmation_checks_size_and_type(mock_client):
    storage = S3Storage("us-west-2", "input-bucket", "output-bucket")
    job = sample_job()
    mock_client.return_value.head_object.return_value = {"ContentLength": 123, "ContentType": "audio/mpeg"}
    assert storage.confirm_upload(job)
    mock_client.return_value.head_object.return_value["ContentLength"] = 122
    assert not storage.confirm_upload(job)


def test_dynamodb_repository_round_trips_job_by_owner():
    table = MagicMock()
    resource = MagicMock()
    resource.Table.return_value = table
    with patch("app.repository.boto3.resource", return_value=resource):
        repository = DynamoJobRepository("jobs", "us-west-2")
        job = sample_job()
        repository.save(job)
        stored = table.put_item.call_args.kwargs["Item"]
        assert "id" not in stored
        assert stored["job_id"] == job.id
        table.get_item.return_value = {"Item": stored}

        restored = repository.get(job.user_sub, job.id)

    assert restored == job
    assert table.get_item.call_args.kwargs["Key"] == {"user_sub": job.user_sub, "job_id": job.id}


def test_s3_key_uses_encoded_owner_and_job_id():
    assert input_object_key(sample_job()) == "users/user%2Fsub/jobs/job-123/input"
