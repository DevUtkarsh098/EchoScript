import os
from datetime import datetime, timezone

import boto3


table = boto3.resource("dynamodb").Table(os.environ["DYNAMODB_TABLE"])


def handler(event, _context):
    table.update_item(
        Key={"user_sub": event["user_sub"], "job_id": event["job_id"]},
        UpdateExpression="SET #status = :failed, updated_at = :updated, error_message = :message",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":failed": "FAILED",
            ":updated": datetime.now(timezone.utc).isoformat(),
            ":message": "Transcription processing failed. Please retry the job.",
        },
    )
    return {"status": "FAILED"}
