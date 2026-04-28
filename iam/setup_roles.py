import json 
import logging

import boto3
from botocore.exceptions import ClientError

from config.settings import Settings

logger = logging.getLogger(__name__)


# Trust Policy - defines who can assume this role
# Allow Lambda (for scheduled runs) and EC2 (for local testing)
TRUST_POLICY = {
    "Version": "2012-10-17", # IAM policy language version 
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": { # who is allowed to assume the role (lambda and ec2 serivces)
                "Service": ["lambda.amazonaws.com", "ec2.amazonaws.com"]
            },
            "Action": "sts:AssumeRole", # Security Token Service 
        }
    ],
}

def build_permission_policy(s3_bucket_name: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "EC2REadAccess",  #sid statement ID
                "Effect": "Allow",
                "Action": ["ec2:DescribeInstances"],
                "Resource": "*",
            },
            {
                "Sid": "EC2StopInstances",
                "Effect": "Allow",
                "Action": ["ec2:StopInstances"],
                "Resource": "*",
            },
            {
                "Sid": "CloudWatchReadAccess",
                "Effect": "Allow",
                "Action": ["cloudwatch: GetMetricStatistics"],
                "Resource": "*",
            
            },
            {
                "Sid": "S3ReportsBucketAccess",
                "Effect": "Allow",
                "Action": [
                    "s3: CreateBucket",
                    "s3: PutObject",
                    "s3: GetObject",
                    "s3: PutBucketLifecycleConfiguration",
                    "s3: HeadBucket",
                ],
                "Resource": [
                    f"arn:aws:s3:::{s3_bucket_name}",
                    f"arn:aws:s3:::{s3_bucket_name}/*",
                ],
                "Resource": "arn:aws:logs:*:*:*",
            },
        ],
    }

class IAMSetup:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.iam = boto3.client("iam", region_name=settings.AWS_REGION)
        self.role_name = settings.MONITOR_ROLE_NAME

    def create_monitor_role(self) -> str:
        role_arn = self._get_existing_role_arn() 
        #  _get_existing_role_arn - check if the roles exist, this makes the script idempotent
        # meaning run the script 10x and it produces the same result without 
        # breaking anything or creating duplicates 
        if role_arn:
            logger.info(f"IAM role '{self.role_name}' already existed: {role_arn}")
        else: 
            logger.info(f"Creating IAM role: {self.role_name}")
            try:
                response = self.iam.create_role(
                    RoleName=self.role_name,
                    AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
                    Description="Least-privilege role for the AWS Health Monitor bot",
                    Tags=[
                        {"Key": "Project", "Value": "aws-health-monitor"},
                        {"Key": "ManagedBy", "Value": "automation-script"},
                    ],
                )
                role_arn = response["Role"]["Arn"]
                logger.info(f"Role created: {role_arn}")
            except ClientError as e:
                logger.error(f"Failed to create role: {e}")
                raise

        self._put_inline_policy()
         # put_role_policy attaches inline policy directly to the role 
        # Use inline instead of managed polocy
        # it keeps permissions tightly coupled to this specific role 
        return role_arn
    
    def _get_existing_role_arn(self) -> str | None: 
        try:
            response = self.iam.get_role(RoleName=self.role_name)
            return response["Role"]["Arn"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                return None
            raise

    def _put_inline_policy(self) -> None:
        policy_document = build_permission_policy(self.settings.S3_BUCKET_NAME)
        try:
            self.iam.put_role_policy(
                RoleName=self.role_name,
                PolicyName="health-monitor-least-privilege",
                PolicyDocument=json.dumps(policy_document),
            )
            logger.info(f"Inline policy applied to role '{self.role_name}' .")
        except ClientError as e:
            logger.error(f"Failed to attach policy: {e}")
            raise 

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    settings = Settings()
    iam_setup = IAMSetup(settings)
    role_arn = iam_setup.create_monitor_role()
    print(f"\nRole ARN: {role_arn}")

    # ARN amaazon resource name 