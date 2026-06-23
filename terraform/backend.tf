terraform {
  required_version = ">= 1.10"
  backend "s3" {
    # use_lockfile requires S3 object locking (enabled on the bucket); no DynamoDB table needed
    bucket       = "log-analytics-service-tfstate-eu-west-1"
    key          = "terraform.tfstate"
    region       = "eu-west-1"
    use_lockfile = true
    encrypt      = true
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "log-analytics-service"
      ManagedBy = "Terraform"
    }
  }
}
