# AWS Resource Health Monitor & Auto-Remediation Bot

A Python automation bot that monitors the AWS environment on a schedule, generates health reports, stores them in S3, and auto-remediates common issues like idle or untagged EC2 instances.

Built to demonstrate real world AWS automation patterns using **boto3**, **IAM least-privilege**, **EC2/S3 APIs**, and **EventBridge scheduling**.

---

# What It Does

| Feature | Description |
|---|---|
| **EC2 Idle Detection** | Queries CloudWatch CPU metrics and flags instances running below a configurable threshold |
| **Tag Enforcement** | Flags EC2 instances missing a required tag (e.g. `Owner`) |
| **Auto-Stop** | Optionally stops idle instances automatically (disabled by default — safe mode) |
| **S3 Reporting** | Uploads a timestamped JSON health report to S3 after every run |
| **Lifecycle Policy** | Automatically expires S3 reports older than 90 days to control costs |
| **Scheduled Runs** | EventBridge rule triggers the bot on a daily cron schedule |
| **Least-Privilege IAM** | Setup script creates an IAM role with only the permissions this bot needs |

---

## Project Structure

```
aws-resource-monitor/
├── main.py                   # Entry point — orchestrates all checks
├── requirements.txt
├── config/
│   └── settings.py           # All configuration via environment variables
├── ec2/
│   └── monitor.py            # EC2 idle detection + auto-stop
├── s3/
│   └── reporter.py           # Report upload + bucket lifecycle management
├── iam/
│   └── setup_roles.py        # Least-privilege IAM role creation
└── eventbridge/
    └── scheduler.py          # EventBridge cron rule management
```

---

## AWS Services & APIs Used

- **EC2** — `describe_instances`, `stop_instances`
- **CloudWatch** — `get_metric_statistics` (CPU utilization)
- **S3** — `create_bucket`, `put_object`, `put_bucket_lifecycle_configuration`, `generate_presigned_url`
- **IAM** — `create_role`, `put_role_policy` (least-privilege inline policy)
- **EventBridge** — `put_rule`, `put_targets` (cron scheduling)

---

## Prerequisites

- Python 3.11+
- AWS credentials configured (`~/.aws/credentials` or environment variables)
- IAM permissions to create roles, S3 buckets, and EventBridge rules (for initial setup)

---

## Setup & Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"
export S3_BUCKET_NAME="my-health-reports"

# Optional: enable auto-stop of idle instances (default is safe/report-only mode)
export EC2_AUTO_STOP_ENABLED="false"

# Idle threshold: flag instances with avg CPU below this % over 24 hours
export EC2_IDLE_CPU_THRESHOLD="5.0"
export EC2_IDLE_HOURS="24"

# Tag enforcement: flag instances missing this tag key
export REQUIRED_TAG_KEY="Owner"
```

### 3. One-time infrastructure setup

Creates the IAM role and S3 bucket, then registers the EventBridge schedule:

```bash
python main.py setup
```

### 4. Run the health check manually

```bash
python main.py
```

### Sample output

```json
{
  "generated_at": "2025-01-15T08:00:00+00:00",
  "account_id": "123456789012",
  "region": "us-east-1",
  "ec2": {
    "total_running": 5,
    "idle_instances": [
      {
        "instance_id": "i-0abc123def456",
        "name": "dev-server-old",
        "type": "t3.medium",
        "avg_cpu_percent": 1.2,
        "observation_hours": 24
      }
    ],
    "untagged_instances": [
      {
        "instance_id": "i-0xyz789",
        "name": "Unnamed",
        "type": "t2.micro",
        "missing_tag": "Owner"
      }
    ],
    "auto_stopped": [],
    "auto_stop_enabled": false
  }
}
```

---

## IAM Permissions (Least Privilege)

The setup script creates a role with only the specific permissions required:

| Permission | Reason |
|---|---|
| `ec2:DescribeInstances` | List running instances |
| `ec2:StopInstances` | Auto-stop idle instances |
| `cloudwatch:GetMetricStatistics` | Fetch CPU utilization |
| `s3:PutObject`, `s3:GetObject` | Upload and read reports |
| `s3:PutBucketLifecycleConfiguration` | Apply 90-day expiry |
| `logs:PutLogEvents` | Write Lambda execution logs |

S3 permissions are scoped to the specific reports bucket — not all S3 resources.

---

## EventBridge Schedule

Default: **daily at 8:00 AM UTC** (`cron(0 8 * * ? *)`)

To change the schedule, set `EVENTBRIDGE_SCHEDULE` before running setup:

```bash
export EVENTBRIDGE_SCHEDULE="cron(0 */6 * * ? *)"  # Every 6 hours
python main.py setup
```

---

## Key Concepts Demonstrated

- **boto3 paginators** for handling large numbers of EC2 instances
- **Least-privilege IAM** with resource-scoped S3 ARNs
- **CloudWatch metrics** queried programmatically via `get_metric_statistics`
- **S3 lifecycle policies** for automated cost management
- **EventBridge cron rules** and Lambda target wiring
- **Idempotent infrastructure scripts** — safe to run multiple times
- **Environment-based configuration** — no hardcoded values

---

## License

MIT
