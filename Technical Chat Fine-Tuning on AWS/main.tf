# Terraform Configuration: VPC, Subnets, IGW, Route Tables, Security Groups,
#                          EC2, S3 Bucket, IAM Roles for EMR

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}


# VARIABLES

variable "net_id" {
  description = "netID prefix. All resources will be prefixed with this."
  type        = string

  validation {
    condition     = length(var.net_id) > 5
    error_message = "net_id must be your Queen's netID"
  }
}

variable "my_ip" {
  description = "Public IP in CIDR form for SSH access."
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
  # default     = "ca-central-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR for the public subnet (EC2 / Ollama / OpenWebUI)."
  type        = string
  default     = "10.0.1.0/24"
}

variable "emr_subnet_cidr" {
  description = "CIDR for the EMR subnet."
  type        = string
  default     = "10.0.2.0/24"
}

variable "ec2_instance_type" {
  description = "EC2 instance type. m5.xlarge for LLM serving."
  type        = string
  default     = "m5.xlarge"
}

variable "ec2_ami" {
  description = "AMI ID."
  type        = string
  default     = "ami-0c7217cdde317cfec"
  # default     = "ami-0da9ffeb885463685"  # with ca-central-1 region
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access."
  type        = string
  default     = "25phxp-keypair"
}


# LOCALS – central name prefix

locals {
  prefix = var.net_id
  tags = {
    Project   = "CISC886"
    NetID     = var.net_id
    ManagedBy = "Terraform"
  }
}

# PROVIDER

provider "aws" {
  region = var.aws_region
}

# DATA SOURCES

# Availability zones in the chosen region
data "aws_availability_zones" "available" {
  state = "available"
}

# SECTION 2 — VPC & NETWORKING

# VPC 

# Using a custom VPC to isolate our resources from other students on the account.
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true   # needed for S3 endpoint and EMR internal DNS
  enable_dns_hostnames = true   # needed so EC2 gets a public DNS name

  tags = merge(local.tags, { Name = "${local.prefix}-vpc" })
}

# Internet Gateway

# Attaching the VPC to the internet. So, the public subnet isn't isolated.
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = merge(local.tags, { Name = "${local.prefix}-igw" })
}

# Public Subnet (EC2 / Ollama / OpenWebUI)

# map_public_ip_on_launch = true so the instance gets a public IP automatically, we also attach an Elastic IP for a stable address.
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = merge(local.tags, { Name = "${local.prefix}-subnet-public" })
}

# EMR Subnet

# Separate /24 subnet for the EMR cluster for isolation.
# EMR needs internet access to download packages, so it also uses the IGW.
resource "aws_subnet" "emr" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.emr_subnet_cidr
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true   # EMR primary node needs a public IP for EMR console

  tags = merge(local.tags, { Name = "${local.prefix}-subnet-emr" })
}

# Route Table (shared public)

# Default route sends all non-local traffic out through the IGW.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = merge(local.tags, { Name = "${local.prefix}-rt-public" })
}

# Associate the route table with the public subnet
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Associate the same route table with the EMR subnet
resource "aws_route_table_association" "emr" {
  subnet_id      = aws_subnet.emr.id
  route_table_id = aws_route_table.public.id
}

# S3 Gateway Endpoint
# Allows EMR to talk to S3 without going over the public internet.
# This is faster, cheaper (no data transfer cost), and more secure.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.public.id]

  tags = merge(local.tags, { Name = "${local.prefix}-s3-endpoint" })
}

# SECURITY GROUPS

# EC2 Security Group
# Only SSH is restricted to our IP. OpenWebUI (3000) and Ollama (11434) are opened so anyone can access them.
resource "aws_security_group" "ec2" {
  name        = "${local.prefix}-sg-ec2"
  description = "Security group for EC2 instance running Ollama + OpenWebUI"
  vpc_id      = aws_vpc.main.id

  # SSH, Our IP only to prevent brute-force attacks
  ingress {
    description = "SSH from our IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  # OpenWebUI – public so anyone can access the chat interface
  ingress {
    description = "OpenWebUI chat interface"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Ollama API – open for curl demo
  ingress {
    description = "Ollama LLM API"
    from_port   = 11434
    to_port     = 11434
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound – EC2 needs to pull from S3, HuggingFace, Ollama registry
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.prefix}-sg-ec2" })
}

# EMR Security Group
resource "aws_security_group" "emr_primary" {
  name        = "${local.prefix}-sg-emr-primary"
  description = "SG for EMR primary node"
  vpc_id      = aws_vpc.main.id

  # SSH for debugging the primary node
  ingress {
    description = "SSH from your IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  # All outbound – EMR needs to reach S3 and internet for packages
  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.prefix}-sg-emr-primary" })
}

resource "aws_security_group" "emr_core" {
  name        = "${local.prefix}-sg-emr-core"
  description = "SG for EMR core/task nodes"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "All outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, { Name = "${local.prefix}-sg-emr-core" })
}

# Self-referencing rules for intra-cluster EMR communication, primary and core traffic on all ports
resource "aws_security_group_rule" "emr_primary_self" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  security_group_id        = aws_security_group.emr_primary.id
  source_security_group_id = aws_security_group.emr_primary.id
  description              = "Intra-cluster: primary to primary"
}

resource "aws_security_group_rule" "emr_core_from_primary" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  security_group_id        = aws_security_group.emr_core.id
  source_security_group_id = aws_security_group.emr_primary.id
  description              = "Intra-cluster: primary to core"
}

resource "aws_security_group_rule" "emr_primary_from_core" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  security_group_id        = aws_security_group.emr_primary.id
  source_security_group_id = aws_security_group.emr_core.id
  description              = "Intra-cluster: core to primary"
}

# SECTION 4 — S3 Bucket (dataset + preprocessed output storage)

resource "aws_s3_bucket" "project" {
  bucket        = "${local.prefix}-cisc886-bucket-v01"
  force_destroy = true  

  tags = merge(local.tags, { Name = "${local.prefix}-cisc886-bucket" })
}

# Block all public access, as dataset and model files should not be public
resource "aws_s3_bucket_public_access_block" "project" {
  bucket                  = aws_s3_bucket.project.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Folder structure 
resource "aws_s3_object" "raw_prefix" {
  bucket  = aws_s3_bucket.project.id
  key     = "data/raw/"
  content = ""
}

resource "aws_s3_object" "processed_prefix" {
  bucket  = aws_s3_bucket.project.id
  key     = "data/output/"
  content = ""
}

resource "aws_s3_object" "models_prefix" {
  bucket  = aws_s3_bucket.project.id
  key     = "models/"
  content = ""
}

# IAM Roles (EC2 + EMR)

# EC2 Instance Profile 
# Allows EC2 to access S3
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2_role" {
  name               = "${local.prefix}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "ec2_s3_access" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${local.prefix}-ec2-instance-profile"
  role = aws_iam_role.ec2_role.name
}

# EMR Service Role
data "aws_iam_policy_document" "emr_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["elasticmapreduce.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "emr_service_role" {
  name               = "${local.prefix}-emr-service-role"
  assume_role_policy = data.aws_iam_policy_document.emr_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "emr_service" {
  role       = aws_iam_role.emr_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole"
}

# EMR EC2 Profile (YARN and nodes)
data "aws_iam_policy_document" "emr_ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "emr_ec2_role" {
  name               = "${local.prefix}-emr-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.emr_ec2_assume_role.json
  tags               = local.tags
}

resource "aws_iam_role_policy_attachment" "emr_ec2_profile_policy" {
  role       = aws_iam_role.emr_ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
}

resource "aws_iam_instance_profile" "emr_ec2_profile" {
  name = "${local.prefix}-emr-ec2-profile"
  role = aws_iam_role.emr_ec2_role.name
}

# SECTION 5 — EC2 Instance (LLM Deployment)

# Elastic IP for a stable public address
resource "aws_eip" "ec2" {
  domain = "vpc"
  tags   = merge(local.tags, { Name = "${local.prefix}-eip" })
}

# User-data script: installs Ollama and OpenWebUI on first boot
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail

    # 1. System update
    apt-get update -y && apt-get upgrade -y

    # 2. Install Docker (used by OpenWebUI)
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
    apt-get update -y
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # 3. Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    systemctl enable ollama
    systemctl start ollama

    # 4. Start OpenWebUI via Docker on port 3000
    #    --add-host=host-docker-internal:host-gateway allows container to reach Ollama on the host
    docker run -d \
      --name open-webui \
      --restart always \
      -p 3000:8080 \
      --add-host=host-docker-internal:host-gateway \
      -e OLLAMA_BASE_URL=http://host-docker-internal:11434 \
      -v open-webui:/app/backend/data \
      ghcr.io/open-webui/open-webui:main

    # 5. Enable Docker on boot (OpenWebUI restarts automatically via --restart always)
    systemctl enable docker

    echo "Bootstrap complete. Ollama: :11434, OpenWebUI: :3000"
  EOF
}

resource "aws_instance" "ec2" {
  ami                         = var.ec2_ami
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.ec2.id]
  iam_instance_profile        = "EMR_EC2_DefaultRole"
  key_name                    = var.key_pair_name != "" ? var.key_pair_name : null
  associate_public_ip_address = true

  # Root volume
  root_block_device {
    volume_size           = 100
    volume_type           = "gp3"
    delete_on_termination = true
    tags                  = merge(local.tags, { Name = "${local.prefix}-ec2-root" })
  }

  user_data = local.user_data

  tags = merge(local.tags, { Name = "${local.prefix}-ec2" })
}

resource "aws_eip_association" "ec2" {
  instance_id   = aws_instance.ec2.id
  allocation_id = aws_eip.ec2.id
}

# OUTPUTS (to ensure resources successful creatiion )

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "Public subnet ID (use this for EC2)"
  value       = aws_subnet.public.id
}

output "emr_subnet_id" {
  description = "EMR subnet ID (use this when creating the EMR cluster in the console)"
  value       = aws_subnet.emr.id
}

output "ec2_public_ip" {
  description = "Elastic IP of the EC2 instance"
  value       = aws_eip.ec2.public_ip
}

output "ec2_instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.ec2.id
}

output "s3_bucket_name" {
  description = "S3 bucket name for datasets and model artifacts"
  value       = aws_s3_bucket.project.bucket
}

output "sg_ec2_id" {
  description = "EC2 security group ID"
  value       = aws_security_group.ec2.id
}

output "emr_sg_primary_id" {
  description = "EMR primary node security group ID (use in EMR console)"
  value       = aws_security_group.emr_primary.id
}

output "emr_sg_core_id" {
  description = "EMR core node security group ID (use in EMR console)"
  value       = aws_security_group.emr_core.id
}

output "emr_service_role_arn" {
  description = "EMR service role ARN (use in EMR console)"
  value       = aws_iam_role.emr_service_role.arn
}

output "emr_ec2_profile_name" {
  description = "EMR EC2 instance profile name (use in EMR console)"
  value       = aws_iam_instance_profile.emr_ec2_profile.name
}

output "openwebui_url" {
  description = "OpenWebUI chat interface URL"
  value       = "http://${aws_eip.ec2.public_ip}:3000"
}

output "ollama_api_url" {
  description = "Ollama API endpoint"
  value       = "http://${aws_eip.ec2.public_ip}:11434"
}

# New EMR Cluster

resource "aws_emr_cluster" "cluster" {
  name           = "${local.prefix}-emr-cluster"
  release_label  = "emr-6.10.0"
  applications   = ["Spark", "Hadoop", "Hive", "JupyterEnterpriseGateway"]
  service_role   = "EMR_DefaultRole"
  
  ec2_attributes {
    # This uses the subnet you already created in your existing code
    subnet_id                         = aws_subnet.public.id 
    emr_managed_master_security_group = aws_security_group.emr_primary.id
    emr_managed_slave_security_group  = aws_security_group.emr_core.id
    instance_profile                  = "EMR_EC2_DefaultRole"
  }

  master_instance_group {
    instance_type = "m4.large"
  }

  core_instance_group {
    instance_type  = "m4.large"
    instance_count = 2
  }

  configurations_json = <<EOF
  [
    {
      "Classification": "spark",
      "Properties": {
        "maximizeResourceAllocation": "true"
      }
    }
  ]
EOF

  tags = local.tags
}

output "emr_cluster_id" {
  value = aws_emr_cluster.cluster.id
}

output "emr_master_public_dns" {
  value = aws_emr_cluster.cluster.master_public_dns
}
