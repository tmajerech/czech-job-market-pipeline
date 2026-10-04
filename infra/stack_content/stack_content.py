from aws_cdk import Stack
from constructs import Construct


class StackContent(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Compose the platform constructs here as they are added.
