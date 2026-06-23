data "aws_availability_zones" "available" {}

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  tags = {
    Name = "vpc-${var.project_name}-${var.environment}"
  }
}

# Two public subnets in different AZs - required by the ALB
resource "aws_subnet" "primary_subnet" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 0)
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet-1-${var.project_name}-${var.environment}"
  }
}

resource "aws_subnet" "secondary_subnet" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 1)
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name = "public-subnet-2-${var.project_name}-${var.environment}"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "igw-${var.project_name}-${var.environment}"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "rt-${var.project_name}-${var.environment}"
  }
}

resource "aws_route_table_association" "primary_subnet" {
  subnet_id      = aws_subnet.primary_subnet.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "secondary_subnet" {
  subnet_id      = aws_subnet.secondary_subnet.id
  route_table_id = aws_route_table.public.id
}

# ALB security group - accepts HTTP from the internet
resource "aws_security_group" "alb" {
  name        = "secgrp-alb-${var.project_name}-${var.environment}"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "secgrp-alb-${var.project_name}-${var.environment}"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ECS security group - accepts traffic on 8080 from the ALB only
resource "aws_security_group" "ecs" {
  name        = "secgrp-ecs-${var.project_name}-${var.environment}"
  description = "Security group for ECS"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "secgrp-ecs-${var.project_name}-${var.environment}"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = 8080
  to_port                      = 8080
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
