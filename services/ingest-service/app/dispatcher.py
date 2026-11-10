import json

import boto3

from .models import Job


class SQSJobDispatcher:
    def __init__(self, queue_url: str, region_name: str):
        if not queue_url:
            raise ValueError("JOB_QUEUE_URL is required for SQS dispatch")
        self.queue_url = queue_url
        self.client = boto3.client("sqs", region_name=region_name)

    def enqueue(self, job: Job) -> None:
        self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps({"user_sub": job.user_sub, "job_id": job.id, "language": job.language}),
        )
