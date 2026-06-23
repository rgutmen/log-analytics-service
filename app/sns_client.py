import json
import os

import boto3


def publish_alert(message: str) -> None:
    """Publish message to the SNS alert topic.

    Requires SNS_TOPIC_ARN environment variable. Raises RuntimeError if not set.
    """
    topic_arn = os.getenv("SNS_TOPIC_ARN")
    if not topic_arn:
        raise RuntimeError("SNS_TOPIC_ARN environment variable is not set")
    boto3.client("sns").publish(
        TopicArn=topic_arn,
        Subject="Log alert triggered",
        Message=message,
    )


def publish_oversized_alert(key: str, size_mb: int) -> None:
    """Publish an SNS notification for a log file skipped due to exceeding the size limit.

    Requires SNS_TOPIC_ARN environment variable. Raises RuntimeError if not set.
    """
    topic_arn = os.getenv("SNS_TOPIC_ARN")
    if not topic_arn:
        raise RuntimeError("SNS_TOPIC_ARN environment variable is not set")
    message = json.dumps({"type": "oversized_file_skipped", "key": key, "size_mb": size_mb})
    boto3.client("sns").publish(
        TopicArn=topic_arn,
        Subject="Oversized log file skipped",
        Message=message,
    )
