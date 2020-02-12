from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_directoryservice as directoryservice,
    aws_iam as iam
)


class AWSManagedADStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']
        internal_sg = props['internal_sg']

        # Managed AD
        aws_managed_ad = directoryservice.CfnMicrosoftAD(
            self, 'AWSManagedAD',
            name=self.node.try_get_context('aws_managed_ad')['domain_name'],
            password=self.node.try_get_context('aws_managed_ad')['admin_password'],
            vpc_settings={
              "subnetIds": vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids,
              "vpcId": vpc.vpc_id
            },
            edition='Standard'
        )

        # クライアント用EC2ホスト
        client_windows = ec2.Instance(
            self, 'ClientWindows',
            instance_type=ec2.InstanceType('t3.large'),
            machine_image=ec2.MachineImage.latest_windows(
                version=ec2.WindowsVersion.WINDOWS_SERVER_2016_JAPANESE_FULL_BASE),
            key_name=self.node.try_get_context('key_name'),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.ISOLATED),
            security_group=internal_sg
        )
        client_windows.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        self.output_props = props.copy()
        self.output_props['aws_managed_ad'] = aws_managed_ad

    @property
    def outputs(self):
        return self.output_props
