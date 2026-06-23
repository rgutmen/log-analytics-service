# Alert topic - subscribers (email, Lambda, etc.) are managed outside Terraform
resource "aws_sns_topic" "logs_notifications" {
  name = "logs-notifications-${var.project_name}-${var.environment}"
}