import aws_cdk as core
import aws_cdk.assertions as assertions

from stack_content import StackContent


def test_stack_can_be_synthesized():
    app = core.App()
    stack = StackContent(app, "JobsPlatformTest")

    assertions.Template.from_stack(stack)
