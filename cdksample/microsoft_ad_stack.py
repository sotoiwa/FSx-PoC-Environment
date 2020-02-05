from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_directoryservice as directoryservice
)


class MicrosoftADStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']

        # MicrosoftAD
        mad = directoryservice.CfnMicrosoftAD(
            self, 'Directory',
            name='corp.example.com',
            password=self.node.try_get_context('microsoft_ad_password'),
            vpc_settings={
              "subnetIds": vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids,
              "vpcId": vpc.vpc_id
            },
            edition='Standard'
        )

        self.output_props = props.copy()

    @property
    def outputs(self):
        return self.output_props
