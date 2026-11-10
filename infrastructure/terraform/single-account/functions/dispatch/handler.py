import json
import os

import boto3
from botocore.exceptions import ClientError


stepfunctions = boto3.client("stepfunctions")


def handler(event, _context):
    failures = []
    state_machine_arn = os.environ["STATE_MACHINE_ARN"]
    for record in event.get("Records", []):
        try:
            message = json.loads(record["body"])
            job_id = message["job_id"]
            stepfunctions.start_execution(
                stateMachineArn=state_machine_arn,
                name=job_id,
                input=json.dumps(message),
            )
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code != "ExecutionAlreadyExists":
                failures.append({"itemIdentifier": record["messageId"]})
        except (KeyError, TypeError, ValueError):
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
