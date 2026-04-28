import logging

import boto3
from botocore.exceptions import ClientError

from config.settings import Settings

logger = logging.getLogger(__name__)

class EventBridgeScheduler:

    def __init__(self, settings: Settings):
        self.settings = settings
        # EventBridge uses the event service name in boto3
        self.events = boto3.client("events", region_name=settings.AWS_REGION)
        self.rule_name = settings.EVENTBRIDGE_RULE_NAME

    def create_schedule(self, lambda_arn: str = None) -> str:
        rule_arn = self._put_rule()

        if lambda_arn:
            self._put_lambda_target(lambda_arn)
        else:
            logger.info(
                "No Lambda ARN provided. Rule created but no target set. "
                "Wire it manually in the AWS console or pass lambda_arn= to this method."
            )

        return rule_arn
    
    def describe_schedule(self) -> dict:
        try: 
            response = self.events.describe_rule(Name=self.rule_name)
            return {
                "name": response["Name"],
                "arn": response["Arn"],
                "schedule": response.get("ScheduleExpression"),
                "state": response.get("State"),
                "description": response.get("Description"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.info(f"Rule '{self.rule_name}' does not exist.")
                return {}
            raise
        
    def disable_schedule(self) -> None:
        try:
            self.events.disable_rule(Name=self.rule_name)
            logger.info(f"EventBridge rule '{self.rule_name}' disabled")
        except ClientError as e:
            logger.error(f"Failed to disable rule: {e}")
            raise

    def enable_schedule(self) -> None:
        try:
            self.events.enable_rule(Name=self.rule_name)
            logger.info(f"EventBridge rule '{self.rule_name}' enabled.")
        except ClientError as e:
            logger.error(f"Failed to enable rule: {e}")
            raise
        
    def delete_schedule(self) -> None:
        try:
            targets = self.events.list_targets_by_rule(
                Rule=self.rule_name
            ).get("Targets", [])

            if targets:
                target_ids = [t["Id"] for t in targets]
                self.events.remove_targets(Rule=self.rule_name, Ids=target_ids)
                logger.info(f"Remove {len(target_ids)} target(s) from rule.")
                
            self.events.delete_rule(Name=self.rule_name)
            logger.info(f"EventBridge rule ' {self.rule_name}' deleted.")
        except ClientError as e:
            logger.error(f"Failed to delete rule: {e}")
            raise 

# the above utility methods are not only a  schedule but a complete management interface
# Enable, disable, describe, delete 

    def _put_rule(self) -> str:
        try:
            response = self.events.put_rule(
                Name=self.rule_name,
                ScheduleExpression=self.settings.EVENTBRIDGE_SCHEDULE,
                State="ENABLED",
                Description="Triggers the AWS Resource Health Monitor daily",
                Tags=[
                    {"Key": "Project", "Value": "aws-health-monitor"},
                    {"Key": "ManagedBy", "Value": "automation-script"},
                ],
            )
            rule_arn = response["RuleArn"]
            logger.info(
                f"EventBridge rule '{self.rule_name}' created. "
                f"Schedule: {self.settings.EVENTBRIDGE_SCHEDULE}"
            )
            return rule_arn
        except ClientError as e:
            logger.error(f"Failed to create EventBridge rule: {e} ")
            raise
        
    def _put_lambda_target(self, lambda_arn: str) -> None:
        try:
            self.events.put_targets(
                Rule=self.rule_name,
                Targets=[
                    {
                        "Id": "health-monitor-lambda-target",
                        "Arn": lambda_arn,
                        "Input": '{"source": "eventbridge-schedule"}',
                        }
                ],
            )
            logger.info(f"Lambda target set: {lambda_arn}")
        except ClientError as e:
            logger.error(f"Failed to set Lambda target: {e}")                
            raise

            # default schedule in settings.py
            # cron(
            # minute = 0
            # hour = 8
            # day-of-month = *
            # month = *
            # day-of-week = ?
            # year = *

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    settings = Settings()
    scheduler = EventBridgeScheduler(settings)

    # create the schedule
    rule_arn = scheduler.create_schedule()
    print(f"\nRule ARN: {rule_arn}")

    # describe it back to confirm
    details = scheduler.describe_schedule()
    print(f"\nSchedule details: {details}")
