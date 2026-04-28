import json
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from config.settings import Settings

logger = logging.getLogger(__name__)


class S3Reporter:

    def __init__(self, settings: Settings):
        self.settings = settings
        self.s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        self.bucket = settings.S3_BUCKET_NAME

    def create_bucket_if_not_exists(self) -> None:
        if self._bucket_exists():
            logger.info(f"Bucket '{self.bucket}' already exists. Skipping.")
            return

        logger.info(f"Creating S3 bucket: {self.bucket}")
        try:
            if self.settings.AWS_REGION == "us-east-1":
                self.s3.create_bucket(Bucket=self.bucket)
            else:
                self.s3.create_bucket(
                    Bucket=self.bucket,
                    CreateBucketConfiguration={
                        "LocationConstraint": self.settings.AWS_REGION
                    },
                )

            self.s3.put_public_access_block(

                Bucket=self.bucket,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": True,
                    "RestrictPublicBuckets": True
                },
            )

            self._apply_lifecycle_policy()
            logger.info(f"Bucket '{self.bucket}' created and configured.")

        except ClientError as e:
            logger.error(f"Failed to create bucket: {e}")
            raise

    def upload_report(self, report: dict[str, Any]) -> str:
        now = datetime.now(tz=timezone.utc)
        key = (
            f"{self.settings.S3_REPORT_PREFIX}"
            f"{now.strftime('%Y/%m/%d')}/"
            f"health-report-{now.strftime('%H-%M-%S')}.json"
        )

        report_with_meta = {
            "generated_at": now.isoformat(),
            **report,
        }

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(report_with_meta, indent=2),
                ContentType="application/json",
            )
            logger.info(f"Report uploaded to s3://{self.bucket}/{key}")

        except ClientError as e:
            logger.error(f"Failed to upload report: {e}")
            raise

        url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=7 * 24 * 3600,
        )

        return url

    def _bucket_exists(self) -> bool:
        try:
            self.s3.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False

    def _apply_lifecycle_policy(self) -> None:
        lifecycle_config = {
            "Rules": [
                {
                    "ID": "expire-old-reports",
                    "Status": "Enabled",
                    "Filter": {"Prefix": self.settings.S3_REPORT_PREFIX},
                    "Expiration": {"Days": 90},
                }
            ]
        }
        try:
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration=lifecycle_config,
            )
            logger.info(
                "Lifecycle policy applied: reports expire after 90 days.")
        except ClientError as e:
            logger.warning(f"Could not apply lifecycle policy: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s %(message)s]"
    )
    settings = Settings()
    reporter = S3Reporter(settings)

    reporter.create_bucket_if_not_exists()

    test_report = {
        "account_id": settings.AWS_ACCOUNT_ID,
        "region": settings.AWS_REGION,
        "ec2": {
            "total_running": 1,
            "idle_instances": [],
            "untagged_instances": [],
            "auto_stop_enabled": False
        }
    }

    url = reporter.upload_report(test_report)
    print(f"\nReport uploaded! Pre-signed URL:\n{url}")
