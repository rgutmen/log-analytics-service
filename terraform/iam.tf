data "aws_iam_policy" "ecs_task_execution" {
  name = "AmazonECSTaskExecutionRolePolicy"
}

# Execution role - used by the ECS agent to pull images and send logs to CloudWatch
resource "aws_iam_role" "ecs_execution" {
  name = "ecs-execution-${var.project_name}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = {
    Name = "ecs-execution-${var.project_name}-${var.environment}"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = data.aws_iam_policy.ecs_task_execution.arn
}

# Task role - used by the container code (boto3) to read logs from S3
resource "aws_iam_role" "ecs_task" {
  name = "ecs-task-${var.project_name}-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = {
    Name = "ecs-task-${var.project_name}-${var.environment}"
  }
}

# Least-privilege S3 access: read-only on the logs bucket only
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "ecs-task-s3-${var.project_name}-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = "arn:aws:s3:::${var.logs_bucket_name}"
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "arn:aws:s3:::${var.logs_bucket_name}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy" "sns_publish" {
  name = "ecs-task-sns-${var.project_name}-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = aws_sns_topic.logs_notifications.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "cloudwatch_app_logs" {
  name = "cloudwatch-app-logs-${var.project_name}-${var.environment}"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "cloudwatch:PutMetricData"
        Resource = "*"
      }
    ]
  })
}