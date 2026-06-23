variable "region" {
  description = "The AWS region to deploy resources in"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "log-analytics-service"
}

variable "environment" {
  description = "The environment to deploy resources in"
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "The VPC CIDR to deploy resources in"
  type        = string
  default     = "10.0.0.0/16"
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "Must be a valid CIDR block."
  }
}

variable "logs_bucket_name" {
  description = "The name of the S3 bucket to store logs"
  type        = string
}

variable "image_tag" {
  description = "The tag of the Docker image to use for the service"
  type        = string
  default     = "latest"
}

variable "desired_count" {
  description = "Amount of desired active services"
  type        = number
  default     = 1
}