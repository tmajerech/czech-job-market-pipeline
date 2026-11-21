from constructs import Construct

from aws_cdk import aws_s3 as s3
from aws_cdk import RemovalPolicy


class StorageConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Compose the storage resources here as they are added.

        self.data_bucket = s3.Bucket(
            self,
            "DataBucket",
            bucket_name="meddea-jobs-data",
            versioned=True,
            # Production should use RETAIN because historical snapshots cannot be
            # reconstructed. DESTROY is intentional while this remains a demo.
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
