import os
import time

import boto3
from botocore.exceptions import ClientError


table = boto3.resource("dynamodb").Table(os.environ["WORKER_SLOTS_TABLE"])


def handler(event, _context):
    now = int(time.time())
    lease_until = now + int(os.environ.get("SLOT_LEASE_SECONDS", "43200"))
    for slot_id in ("slot-0", "slot-1"):
        try:
            table.update_item(
                Key={"slot_id": slot_id},
                UpdateExpression="SET job_id = :job, lease_expires = :lease",
                ConditionExpression="attribute_not_exists(job_id) OR lease_expires < :now",
                ExpressionAttributeValues={":job": event["job_id"], ":lease": lease_until, ":now": now},
            )
            return {"acquired": True, "slot_id": slot_id}
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise
    return {"acquired": False, "slot_id": None}
