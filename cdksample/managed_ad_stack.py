from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_directoryservice as directoryservice,
    aws_iam as iam
)


class ManagedADStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']
        internal_sg = props['internal_sg']

        # Managed AD
        managed_ad = directoryservice.CfnMicrosoftAD(
            self, 'ManagedAD',
            name='corp.example.com',
            password=self.node.try_get_context('managed_ad_password'),
            vpc_settings={
              "subnetIds": vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids,
              "vpcId": vpc.vpc_id
            },
            edition='Standard'
        )

        # クライアント用EC2ホスト
        mad_client_windows = ec2.Instance(
            self, 'ManagedADClientWindows',
            instance_type=ec2.InstanceType('t3.large'),
            machine_image=ec2.WindowsImage(version=ec2.WindowsVersion.WINDOWS_SERVER_2012_R2_RTM_JAPANESE_64BIT_BASE),
            key_name=self.node.try_get_context('key_name'),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.ISOLATED),
            security_group=internal_sg
        )
        mad_client_windows.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        self.output_props = props.copy()
        self.output_props['managed_ad'] = managed_ad

    @property
    def outputs(self):
        return self.output_props
