import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
# botocore is the library for boto3, clienterror is the exception AWS raises when something goes wrong (user doesnt have permission or resource doesn't exist)
from botocore.exceptions import ClientError

from config.settings import Settings

# this creates a logger named after the current file, when this module prints log messages,
# the output will tell you where it came from. Professionals use logging instead of print()
logger = logging.getLogger(__name__)


class EC2Monitor:

    def __init__(self, settings: Settings):
        self.settings = settings
        # creates a connection to the EC2 API for a specific region
        self.ec2 = boto3.client('ec2', region_name=settings.AWS_REGION)
        self.cloudwatch = boto3.client(
            'cloudwatch', region_name=settings.AWS_REGION)

    def _get_all_running_instances(self) -> list[dict]:
        instances = []
        paginator = self.ec2.get_paginator('describe_instances')

        try:
            for page in paginator.paginate(
                Filters=[{'Name': 'instance-state-name', 'Values': ["running"]}]
            ):
                for reservation in page['Reservations']:
                    instances.extend(reservation['Instances'])
        except ClientError as e:
            logger.error(f'Failed to describe EC2 instances: {e}')

        return instances


# Paginators - AWS APIs don't return all results at once if there are hundreds of them
# a page of results is returned with a token to get the next page
# the paginator handles this automatically, no need to write a loop

# Filters - filtering in python allow you to return running instances only
# instead of getting every instance. Filteering ath the API level is better, faster, and cheaper

# Reservations - EC2 doesn't return a flat list of instances, instead it
# wraps them into reservations. So you have to loop through reservations, then
# then loop through instances inside each reservations
# the instances.extend() call flattens them into one list.


    def _get_average_cpu(self, instance_id: str) -> float | None:
        end_time = datetime.now(tz=timezone.utc)
        start_time = end_time - timedelta(hours=self.settings.EC2_IDLE_HOURS)

        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',  # CloudWatch metric
                MetricName='CPUUtilization',  # CloudWatch metric
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # groups data points in 1 hour blocks (3600 sec)
                Statistics=['Average'],
            )
        except ClientError as e:
            logger.error(f'CloudWatch query failed for {instance_id}: {e}')
            return None

        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return None

        # pyton gnerator expression, it loops through all the hourly data points and
        # calculates the overall average CPU across the whole observatio window.
        avg_cpu = sum(dp['Average'] for dp in datapoints) / len(datapoints)
        return avg_cpu

    def _stop_instance(self, instance_id: str, name: str) -> bool:
        try:
            self.ec2.stop_instances(InstanceIds=[instance_id])
            logger.info(
                f'AUTO-STOP: Stopped idle instance {instance_id} ({name})')
            return True

        except ClientError as e:
            logger.error(f'Failed to stop instance {instance_id}: {e}')
            return False

    def run(self) -> dict[str, Any]:
        instances = self._get_all_running_instances()
        logger.info(f'Found {len(instances)} running EC2 instance(s).')

        idle_instances = []
        untagged_instances = []
        stopped_instances = []

        for instance in instances:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}
            name = tags.get("Name", "Unnamed")

            if self.settings.REQUIRED_TAG_KEY not in tags:
                logger.warning(
                    f"Instance {instance_id} ({name}) is missing tag '{self.settings.REQUIRED_TAG_KEY}'")
                untagged_instances.append({
                    'instance_id': instance_id,
                    'name': name,
                    'type': instance_type,
                    'missing_tag': self.settings.REQUIRED_TAG_KEY
                })

            avg_cpu = self._get_average_cpu(instance_id)
            if avg_cpu is not None and avg_cpu < self.settings.EC2_IDLE_CPU_THRESHOLD:
                logger.warning(
                    f'Instance {instance_id} ({name}) is idle: avg CPU = {avg_cpu: 2f}%')
                idle_instances.append({
                    'instance_id': instance_id,
                    'name': name,
                    'type': instance_type,
                    'avg_cpu_percent': round(avg_cpu, 2),
                })

                if self.settings.EC2_AUTO_STOP_ENABLED:
                    success = self._stop_instance(instance_id, name)
                    if success:
                        stopped_instances.append(instance_id)

        return {
            'total_running': len(instances),
            'idle_instances': idle_instances,
            'untagged_instances': untagged_instances,
            'auto_stopped': stopped_instances,
            'auto_stop_enabled': self.settings.EC2_AUTO_STOP_ENABLED
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    settings = Settings()
    monitor = EC2Monitor(settings)
    report = monitor.run()
    print(report)
