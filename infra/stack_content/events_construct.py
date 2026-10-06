from aws_cdk import TimeZone
from aws_cdk import aws_scheduler as scheduler
from aws_cdk import aws_scheduler_targets as targets
from constructs import Construct

from .ingestion_construct import IngestionConstruct


class Events(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        ingestion: IngestionConstruct,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.download_schedule = scheduler.Schedule(
            self,
            "DailyDownload",
            schedule=scheduler.ScheduleExpression.cron(
                hour="5",  # The file does not have release time but seems to be around 1am
                minute="0",
                time_zone=TimeZone.EUROPE_PRAGUE,
            ),
            target=targets.StepFunctionsStartExecution(
                ingestion.download_state_machine
            ),
        )
