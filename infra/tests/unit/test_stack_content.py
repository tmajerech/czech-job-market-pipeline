import aws_cdk as core
import aws_cdk.assertions as assertions

from stack_content import StackContent


def test_stack_can_be_synthesized():
    app = core.App()
    stack = StackContent(app, "JobsPlatformTest")

    template = assertions.Template.from_stack(stack)
    lambda_resources = template.find_resources("AWS::Lambda::Function")
    application_lambdas = [
        resource
        for resource in lambda_resources.values()
        if resource["Properties"].get("Handler") == "index.lambda_handler"
    ]

    assert len(application_lambdas) == 1
    assert "TransformSnapshot" not in str(template.to_json())
