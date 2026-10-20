from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import BundlingOptions, PythonFunction
from pathlib import Path
from aws_cdk import Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_

from .storage_construct import StorageConstruct

INFRA_ROOT = Path(__file__).resolve().parents[1]


class LambdasConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        storage: StorageConstruct,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Compose the lambda functions here as they are added.

        self.download_snapshot = PythonFunction(
            self,
            "DownloadSnapshot",
            entry=str(INFRA_ROOT / "handlers" / "download_snapshot"),
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_14,
            timeout=Duration.minutes(5),
            memory_size=128,
            environment={"DATA_BUCKET_NAME": storage.data_bucket.bucket_name},
            bundling=BundlingOptions(
                asset_excludes=["__pycache__", "*.pyc"],
            ),
        )

        self.transform_snapshot = PythonFunction(
            self,
            "TransformSnapshot",
            entry=str(INFRA_ROOT / "handlers" / "transform_snapshot"),
            index="index.py",
            handler="lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_14,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={"DATA_BUCKET_NAME": storage.data_bucket.bucket_name},
            bundling=BundlingOptions(
                asset_excludes=["__pycache__", "*.pyc"],
            ),
        )

        storage.data_bucket.grant_read_write(self.transform_snapshot)
        storage.data_bucket.grant_read_write(self.download_snapshot)
