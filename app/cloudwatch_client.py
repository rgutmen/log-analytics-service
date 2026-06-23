import os

import boto3


def publish_metrics(total: int, alert: bool) -> None:
    """Publish ErrorCount and AlertTriggered metrics to CloudWatch under the LogAnalytics namespace."""
    env = os.getenv("ENVIRONMENT", "unknown")
    boto3.client("cloudwatch").put_metric_data(
        Namespace="LogAnalytics",
        MetricData=[
            {
                "MetricName": "ErrorCount",
                "Value": total,
                "Unit": "Count",
                "Dimensions": [{"Name": "Environment", "Value": env}],
            },
            {
                "MetricName": "AlertTriggered",
                "Value": 1 if alert else 0,
                "Unit": "Count",
                "Dimensions": [{"Name": "Environment", "Value": env}],
            },
        ],
    )
