resource "aws_lb" "main" {
  name               = "alb-${var.project_name}-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.primary_subnet.id, aws_subnet.secondary_subnet.id]

  # Prevents accidental deletion via Terraform; disable manually before destroy
  enable_deletion_protection = true

  tags = {
    Name = "alb-${var.project_name}-${var.environment}"
  }
}

# target_type = "ip" is required for Fargate (tasks get IPs, not instance IDs)
resource "aws_lb_target_group" "app" {
  name        = "tg-${var.project_name}-${var.environment}"
  target_type = "ip"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id

  health_check {
    path = "/health"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
