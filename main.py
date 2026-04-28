import logging
from config.settings import Settings
from ec2.monitor import EC2Monitor
from s3.reporter import S3Reporter
from iam.setup_roles import IAMSetup
from eventbridge.scheduler import EventBridgeScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_health_check():
    """
    Main health check routine. Runs EC2 checks and uploads
    the report to S3. Called by EventBridge on a schedule,
    or manually from the command line.
    """
    logger.info("Starting AWS Resource Health Monitor...")

    settings = Settings()
    reporter = S3Reporter(settings)
    ec2_monitor = EC2Monitor(settings)

    # run EC2 health checks
    logger.info("Running EC2 health checks...")
    ec2_report = ec2_monitor.run()

    # compile full report 
    full_report = {
        "account_id": settings.AWS_ACCOUNT_ID,
        "region": settings.AWS_REGION,
        "ec2": ec2_report,
    }

    # upload report to S3
    logger.info("Uploading health report to S3...")
    report_url = reporter.upload_report(full_report)
    logger.info(f"Report saved: {report_url}")

    logger.info("Health check complete.")
    return full_report

def setup_infrastructure():
    """
    One-time setup. Creates IAM roles, s3 bucket, and 
    EventBridge schedule. Run this code once before deploying.
    """

    logger.info("Setting up AWS infrastructure...")

    settings = Settings()

    iam_setup = IAMSetup(settings)
    iam_setup.create_monitor_role()

    reporter = S3Reporter(settings)
    reporter.create_bucket_if_not_exists()

    scheduler = EventBridgeScheduler(settings)
    scheduler.create_schedule()

    logger.info("Infrastructure setup complete.")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "setup":
    # sys.argv - lsit of arguments passed to the script from the terminal
    # [0] script name
    # [1] first argument  
        setup_infrastructure()
    else:
        run_health_check()