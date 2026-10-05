from aws_cdk import Stack
from constructs import Construct

from .lambdas_construct import LambdasConstruct
from .storage_construct import StorageConstruct


class StackContent(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.storage = StorageConstruct(self, "StorageConstruct")
        self.lambdas = LambdasConstruct(self, "LambdasConstruct", self.storage)
