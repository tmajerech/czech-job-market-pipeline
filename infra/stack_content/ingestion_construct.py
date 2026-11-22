from aws_cdk import aws_stepfunctions as stepfunctions
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

from .lambdas_construct import LambdasConstruct


class IngestionConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        lambdas: LambdasConstruct,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        download_snapshot = tasks.LambdaInvoke(
            self,
            "DownloadSnapshot",
            lambda_function=lambdas.download_snapshot,  # type: ignore
            payload_response_only=True,
        )

        self.download_state_machine = stepfunctions.StateMachine(
            self,
            "DownloadStateMachine",
            definition_body=stepfunctions.DefinitionBody.from_chainable(
                download_snapshot
            ),
        )
