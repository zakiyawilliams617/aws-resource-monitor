import os


class Settings:
    # VARIABLE_NAME = os.getenv('VARIABLE_NAME', 'default value')
    AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID', '877295423290')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'my-health-reports')
    S3_REPORT_PREFIX = os.getenv('S3_REPORT_PREFIX', 'reports/')
    EC2_IDLE_CPU_THRESHOLD = float(os.getenv('EC2_IDLE_CPU_THRESHOLD', '5.0'))
    EC2_IDLE_HOURS = int(os.getenv("EC2_IDLE_HOURS", "24"))
    EC2_AUTO_STOP_ENABLED = os.getenv(
        'EC2_AUTO_STOP_ENABLED', 'false').lower() == 'true'
    REQUIRED_TAG_KEY = os.getenv('REQUIRED_TAG_KEY', 'Owner')
    MONITOR_ROLE_NAME = os.getenv(
        'MONITOR_ROLE_NAME', 'aws-health-monitor-role')
    EVENTBRIDGE_SCHEDULE = os.getenv(
        'EVENTBRIDGE_SCHEDULE', 'cron(0 8 * * ? *)')
    EVENTBRIDGE_RULE_NAME = os.getenv(
        'EVENTBRIDGE_RULE_NAME', 'aws-health-monitor-schedule')
