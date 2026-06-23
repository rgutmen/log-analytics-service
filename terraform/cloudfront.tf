locals {
  alb_origin_id = "alb-${var.project_name}"
}

resource "aws_cloudfront_distribution" "cdn" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "${var.project_name}-${var.environment}"

  # ALB is HTTP-only; TLS terminates at CloudFront
  origin {
    domain_name = aws_lb.main.dns_name
    origin_id   = local.alb_origin_id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = local.alb_origin_id

    # CachingDisabled: this is an API, results change with every log upload
    cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"

    # AllViewerExceptHostHeader: forwards query strings and headers to the ALB
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"

    viewer_protocol_policy = "redirect-to-https"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
      locations        = []
    }
  }

  # No custom domain - using the default CloudFront certificate
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "cdn-${var.project_name}-${var.environment}"
  }
}
