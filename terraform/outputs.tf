output "cloudfront_url" {
  value       = aws_cloudfront_distribution.cdn.domain_name
  description = "Domain name of the CloudFront distribution"
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "URL of the ECR repository"
}

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "DNS name of the Application Load Balancer"
}
