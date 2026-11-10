import json
from pathlib import Path
from threading import RLock
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

from .models import Job


class LocalJobRepository:
    def __init__(self, data_dir: Path):
        self.root = data_dir / "status"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, user_sub: str, job_id: str) -> Path:
        return self.root / user_sub.replace("/", "_") / f"{job_id}.json"

    def save(self, job: Job) -> Job:
        path = self._path(job.user_sub, job.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        with self._lock:
            temporary.write_text(job.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(path)
        return job

    def get(self, user_sub: str, job_id: str) -> Job | None:
        path = self._path(user_sub, job_id)
        if not path.exists():
            return None
        with self._lock:
            return Job.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self, user_sub: str) -> list[Job]:
        folder = self._path(user_sub, "placeholder").parent
        if not folder.exists():
            return []
        with self._lock:
            jobs = [Job.model_validate(json.loads(path.read_text(encoding="utf-8"))) for path in folder.glob("*.json")]
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)


class DynamoJobRepository:
    def __init__(self, table_name: str, region_name: str):
        if not table_name:
            raise ValueError("DYNAMODB_TABLE is required for the DynamoDB repository")
        self.table = boto3.resource("dynamodb", region_name=region_name).Table(table_name)

    def save(self, job: Job) -> Job:
        item = job.model_dump(mode="json")
        item["job_id"] = item.pop("id")
        self.table.put_item(Item=_dynamo_safe(item))
        return job

    def get(self, user_sub: str, job_id: str) -> Job | None:
        response = self.table.get_item(Key={"user_sub": user_sub, "job_id": job_id}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return None
        item["id"] = item.pop("job_id")
        return Job.model_validate(item)

    def list(self, user_sub: str) -> list[Job]:
        jobs: list[Job] = []
        query: dict = {"KeyConditionExpression": Key("user_sub").eq(user_sub)}
        while True:
            response = self.table.query(**query)
            for item in response.get("Items", []):
                item["id"] = item.pop("job_id")
                jobs.append(Job.model_validate(item))
            key = response.get("LastEvaluatedKey")
            if not key:
                break
            query["ExclusiveStartKey"] = key
        return sorted(jobs, key=lambda item: item.created_at, reverse=True)


def build_repository(settings):
    backend = settings.repository_backend.lower()
    if backend == "dynamodb":
        return DynamoJobRepository(settings.dynamodb_table, settings.aws_region)
    if backend == "local":
        return LocalJobRepository(settings.data_dir)
    raise ValueError(f"Unsupported repository backend: {settings.repository_backend}")


def _dynamo_safe(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _dynamo_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_dynamo_safe(item) for item in value]
    return value

