import os

import boto3


table = boto3.resource("dynamodb").Table(os.environ["WORKER_SLOTS_TABLE"])


def handler(event, _context):
    table.update_item(
        Key={"slot_id": event["slot_id"]},
        UpdateExpression="REMOVE job_id, lease_expires",
        ConditionExpression="job_id = :job",
        ExpressionAttributeValues={":job": event["job_id"]},
    )
    return {"released": True}
