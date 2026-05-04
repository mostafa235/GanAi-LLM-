# CISC 886 – Cloud Computing Project
**School of Computing, Queen's University, Kingston, Canada**  
**AWS Region**: `us-east-1`

---

## Project Overview

An end-to-end cloud-based chat assistant built on AWS. The pipeline covers infrastructure provisioning (Terraform), distributed data preprocessing (PySpark on EMR), local model fine-tuning (Unsloth + QLoRA), model deployment (Ollama on EC2), and a live browser chat interface (OpenWebUI).

---

## Repository Structure

```
cisc886-25phxp/
├── README.md
├── terraform/
│   └── main.tf                    # All AWS infrastructure
├── pyspark/
│   └── emr_spark_preprocessing.py              # PySpark preprocessing pipeline
├── notebooks/
│   ├── model_finetuning.ipynb    # Local fine-tuning notebook
│   └── data_eda.ipynb            # EDA notebook
├── eda/
└── report/
    └── report.pdf
```

---

## Prerequisites

### Tools (install on your local machine)
| Tool | Version | Install |
|------|---------|---------|
| Terraform | ≥ 1.5.0 | https://developer.hashicorp.com/terraform/install |
| AWS CLI | v2 | https://aws.amazon.com/cli/ |
| Python | ≥ 3.9 | https://python.org |
| Git | any | https://git-scm.com |

### AWS Requirements
- Access to the shared CISC 886 AWS account (`us-east-1` region)
- An EC2 key pair named `25phxp-keypair` created in the AWS Console before running Terraform
- Sufficient IAM permissions to create VPC, EC2, EMR, S3, and IAM resources

### Accounts
- HuggingFace account (free) — for dataset access
- GitHub account — for repository hosting

---

## Phase 1 — Infrastructure Provisioning (Terraform)

### Step 1.1 — Create EC2 Key Pair (one-time, via AWS Console)

1. Go to **EC2 → Key Pairs → Create key pair**
2. Name: `25phxp-keypair`
3. Format: `.pem`
4. Download and secure it:
```bash
chmod 400 25phxp-keypair.pem
```

### Step 1.2 — Configure AWS CLI

```bash
aws configure
# Enter: Access Key ID, Secret Access Key, region: us-east-1, output: json
```

### Step 1.3 — Deploy infrastructure with Terraform

```bash
cd terraform/

# Initialise providers
terraform init

# Find your public IP
MY_IP=$(curl -s https://checkip.amazonaws.com)/32
echo "Your IP: $MY_IP"

# Preview all resources to be created
terraform plan \
  -var="net_id=25phxp" \
  -var="my_ip=$MY_IP"

# Deploy (takes ~3-5 minutes)
terraform apply \
  -var="net_id=25phxp" \
  -var="my_ip=$MY_IP"
```

### Step 1.4 — Save Terraform outputs

After apply completes, note these values (you will need them in later phases):

```bash
terraform output
```

Key outputs:
- `ec2_public_ip` — Elastic IP of your deployment instance
- `emr_subnet_id` — subnet ID for EMR cluster creation
- `emr_sg_primary_id` — EMR primary node security group
- `emr_sg_core_id` — EMR core node security group
- `s3_bucket_name` — `25phxp-cisc886-bucket`
- `emr_cluster_id` — EMR cluster ID (created by Terraform)

### What Terraform creates

| Resource | Name | Purpose |
|----------|------|---------|
| VPC | `25phxp-vpc` | Isolated network (`10.0.0.0/16`) |
| Internet Gateway | `25phxp-igw` | Internet access for both subnets |
| Public Subnet | `25phxp-subnet-public` | EC2 instance (`10.0.1.0/24`, `us-east-1a`) |
| EMR Subnet | `25phxp-subnet-emr` | EMR cluster (`10.0.2.0/24`, `us-east-1b`) |
| Route Table | `25phxp-rt-public` | Routes `0.0.0.0/0` to IGW |
| S3 Gateway Endpoint | `25phxp-s3-endpoint` | Private S3 access from EMR/EC2 |
| Security Group | `25phxp-sg-ec2` | EC2: SSH(22), OpenWebUI(3000), Ollama(11434) |
| Security Group | `25phxp-sg-emr-primary` | EMR primary node rules |
| Security Group | `25phxp-sg-emr-core` | EMR core node rules |
| S3 Bucket | `25phxp-cisc886-bucket` | Dataset storage + model artifacts |
| EC2 Instance | `25phxp-ec2` | `m5.xlarge`, Ubuntu 22.04, 100 GB gp3 |
| Elastic IP | `25phxp-eip` | Stable public IP for EC2 |
| IAM Role | `25phxp-emr-service-role` | EMR service permissions |
| IAM Role | `25phxp-emr-ec2-role` | EMR node S3 access |
| EMR Cluster | `25phxp-emr-cluster` | `emr-6.10.0`, 1× primary + 2× core `m4.large` |

---

## Phase 2 — Data Preprocessing with PySpark on EMR

### Step 2.1 — Upload PySpark script to S3

```bash
aws s3 cp pyspark/emr_spark_preprocessing.py \
  s3://25phxp-cisc886-bucket/scripts/emr_spark_preprocessing.py
```

### Step 2.2 — Submit the Spark job as an EMR Step

```bash
# Get the cluster ID from Terraform output
CLUSTER_ID=$(cd terraform && terraform output -raw emr_cluster_id)

aws emr add-steps \
  --cluster-id $CLUSTER_ID \
  --steps Type=Spark,\
Name="25phxp-preprocess",\
ActionOnFailure=CONTINUE,\
Args=[--deploy-mode,cluster,\
--conf,spark.pyspark.python=python3,\
s3://25phxp-cisc886-bucket/scripts/emr_spark_preprocessing.py]
```

### Step 2.3 — Monitor the job

```bash
# Watch step status (repeat until status = COMPLETED)
aws emr describe-step \
  --cluster-id $CLUSTER_ID \
  --step-id <STEP_ID_FROM_ABOVE>
```

Expected runtime: **20–25 minutes**

### Step 2.4 — Verify output files in S3

```bash
aws s3 ls s3://25phxp-cisc886-bucket/data/processed/ --recursive --human-readable
# Expected: ~200 MB total across train/, val/, test/ parquet files
```

### Step 2.5 — CRITICAL: Terminate the EMR cluster

```bash
aws emr terminate-clusters --cluster-ids $CLUSTER_ID

# Confirm terminated status
aws emr describe-cluster \
  --cluster-id $CLUSTER_ID \
  --query "Cluster.Status.State"
# Expected output: "TERMINATED"
```


### About the Dataset

- **Source**: `https://huggingface.co/datasets/kispeterzsm-szte/stackexchange/tree/main` on HuggingFace
- **Subsets used**: `ai`, `cs`, `cstheory`, `datascience`, `askubuntu`, `codegolf`, `dba`, `stackoverflow`
- The PySpark script downloads the dataset **directly from HuggingFace inside the EMR cluster** at job runtime — no manual upload to S3 is required before this step
- Processed output (~200 MB) is written directly to S3 in Parquet format

---

## Phase 3 — Model Fine-Tuning (Local)

Fine-tuning was performed **locally** (not on AWS) using Unsloth and QLoRA to avoid cloud GPU costs.

### Step 3.1 — Install dependencies locally

```bash
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps trl peft accelerate bitsandbytes datasets
```

### Step 3.2 — Run the fine-tuning notebook

Open `notebooks/model_finetuning.ipynb` in Jupyter and run all cells.

The notebook:
1. Loads `Qwen/Qwen2.5-1.5B-Instruct` as the base model in 4-bit quantisation
2. Attaches LoRA adapters (rank 16) via Unsloth's `get_peft_model`
3. Loads the processed training split from S3 (or locally)
4. Fine-tunes using `SFTTrainer` for 1 epoch
5. Exports the fine-tuned model to GGUF format (`Q4_K_M` quantisation)

### Step 3.3 — Upload the GGUF model to S3

```bash
aws s3 cp 25phxp-finetuned-q4_k_m.gguf \
  s3://25phxp-cisc886-bucket/models/25phxp-finetuned-q4_k_m.gguf
```

Verify the upload:
```bash
aws s3 ls s3://25phxp-cisc886-bucket/models/ --human-readable
```

---

## Phase 4 — Model Deployment on EC2

### Step 4.1 — SSH into the EC2 instance

```bash
ssh -i 25phxp-keypair.pem ubuntu@<EC2_PUBLIC_IP>
# EC2_PUBLIC_IP comes from: terraform output ec2_public_ip
```

### Step 4.2 — Verify Ollama and OpenWebUI are running

The `user_data` script in `main.tf` installs both automatically on first boot. Verify:

```bash
# Check Ollama service
systemctl status ollama
# Expected: active (running)

# Check OpenWebUI Docker container
docker ps
# Expected: open-webui container, Up, port 3000->8080
```

> If the instance was just launched, wait ~3 minutes for the user_data bootstrap to complete before checking.

### Step 4.3 — Pull the GGUF model from S3

```bash
aws s3 cp s3://25phxp-cisc886-bucket/models/25phxp-finetuned-q4_k_m.gguf \
          /home/ubuntu/25phxp-finetuned-q4_k_m.gguf
```

### Step 4.4 — Create a Modelfile and register with Ollama

```bash
cat > /home/ubuntu/Modelfile <<'EOF'
FROM /home/ubuntu/25phxp-finetuned-q4_k_m.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM "You are a helpful assistant fine-tuned by 25phxp on StackExchange Q&A data for CISC 886."
EOF

ollama create 25phxp-model -f /home/ubuntu/Modelfile

# Verify the model is registered
ollama list
```

### Step 4.5 — Test via terminal

```bash
# Interactive test
ollama run 25phxp-model "What is the difference between a process and a thread?"
```

### Step 4.6 — Test via curl

```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "25phxp-model",
    "prompt": "Explain what a VPC is in simple terms.",
    "stream": false
  }'
```

---

## Phase 5 — Web Interface (OpenWebUI)

### Step 5.1 — Access the interface

Open in any browser:
```
http://<EC2_PUBLIC_IP>:3000
```

### Step 5.2 — Initial setup

1. Create an admin account on the first-visit registration screen
2. Go to **Settings → Connections**
3. Set Ollama API URL to: `http://host-docker-internal:11434`
4. Select model: `25phxp-model`

### Step 5.3 — Verify auto-restart

OpenWebUI runs as a Docker container with `--restart always`, and Docker is enabled via `systemctl enable docker`. To verify:

```bash
sudo reboot
# Wait 90 seconds
# Re-open http://<EC2_PUBLIC_IP>:3000 in browser
# Interface should be available without any manual intervention
```

---

## Phase 6 — Teardown

```bash
# 1. On the EC2 instance: remove large model files to avoid S3 storage charges
aws s3 rm s3://25phxp-cisc886-bucket/models/25phxp-finetuned-q4_k_m.gguf

# 2. Destroy all Terraform-managed infrastructure
cd terraform/
terraform destroy \
  -var="net_id=25phxp" \
  -var="my_ip=$(curl -s https://checkip.amazonaws.com)/32"

# 3. Confirm no resources remain
aws ec2 describe-instances \
  --filters "Name=tag:NetID,Values=25phxp" \
  --query "Reservations[].Instances[].State.Name"
```

---

## Cost Summary

All costs are based on **us-east-1** on-demand pricing. Actual charges may vary slightly.

### EMR Cluster

| Component | Instance | Count | Rate | Hours | Cost |
|-----------|----------|-------|------|-------|------|
| EC2 – Primary node | `m4.large` | 1 | $0.100/hr | 2 | $0.20 |
| EC2 – Core nodes | `m4.large` | 2 | $0.100/hr | 2 | $0.40 |
| EMR surcharge – Primary | `m4.large` | 1 | $0.021/hr | 2 | $0.04 |
| EMR surcharge – Core | `m4.large` | 2 | $0.021/hr | 2 | $0.08 |
| **EMR Subtotal** | | | | | **$0.72** |

### EC2 Deployment Instance

| Component | Detail | Rate | Hours | Cost |
|-----------|--------|------|-------|------|
| EC2 `m5.xlarge` | Deployment + serving | $0.192/hr | 1 | $0.19 |
| EBS `gp3` 100 GB | Root volume | $0.008/GB-hr | 1 | $0.00 |
| Elastic IP | Associated with instance | $0.005/hr | 1 | $0.01 |
| **EC2 Subtotal** | | | | **$0.20** |

### Storage & Transfer

| Component | Detail | Rate | Amount | Cost |
|-----------|--------|------|--------|------|
| S3 Storage | ~1.15 GB (940 MB model + ~200 MB processed data) | $0.023/GB-month | 1.15 GB | $0.03 |
| S3 PUT requests | Script upload, parquet writes | $0.005/1000 | ~500 | $0.00 |
| S3 GET requests | EMR reads, EC2 model pull | $0.0004/1000 | ~200 | $0.00 |
| Data transfer OUT | Model pull EC2←S3 (~1 GB GGUF) | $0.09/GB | 1 GB | $0.09 |
| **Storage Subtotal** | | | | **$0.12** |

### Grand Total

| Category | Cost |
|----------|------|
| EMR Cluster (2 hrs) | $0.72 |
| EC2 Deployment (1 hr) | $0.20 |
| Storage & Transfer | $0.12 |
| **Total Estimated** | **~$1.04** |

> Note: Fine-tuning was performed **locally** — no cloud GPU costs were incurred. If fine-tuning were done on a cloud GPU instance (e.g. `g4dn.xlarge` at $0.526/hr), an additional ~$2–5 would apply depending on training duration.

---

## Quick Reference

```bash
# SSH to EC2
ssh -i 25phxp-keypair.pem ubuntu@<EC2_PUBLIC_IP>

# Chat interface
http://<EC2_PUBLIC_IP>:3000

# Ollama API
curl http://<EC2_PUBLIC_IP>:11434/api/tags

# S3 bucket
aws s3 ls s3://25phxp-cisc886-bucket/ --recursive --human-readable

# EMR cluster status
aws emr describe-cluster --cluster-id <CLUSTER_ID> --query "Cluster.Status.State"
```
