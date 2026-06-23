resource "aws_cloudwatch_log_group" "app" {
  name              = "log-group-${var.project_name}-${var.environment}"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  name = "ecs-${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "app" {
  family                   = "task-${var.project_name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = templatefile("${path.module}/task-definition.json", {
    image_url     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
    aws_region    = var.region
    log_group     = aws_cloudwatch_log_group.app.name
    project_name  = var.project_name
    environment   = var.environment
    sns_topic_arn = aws_sns_topic.logs_notifications.arn
  })
}

resource "aws_ecs_service" "app" {
  name            = "ecs-service-${var.project_name}-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  task_definition = aws_ecs_task_definition.app.arn

  # Public subnets + public IP: avoids NAT gateway cost for a test environment
  network_configuration {
    subnets          = [aws_subnet.primary_subnet.id, aws_subnet.secondary_subnet.id]
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "log-analytics"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  # CI/CD manages task definition revisions; ignore_changes prevents Terraform from
  # reverting to the initial revision on unrelated applies
  lifecycle {
    ignore_changes = [task_definition]
  }
}
