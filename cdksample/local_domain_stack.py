from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam
)


class LocalDomainStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']
        internal_sg = props['internal_sg']

        # EC2の作成
        # https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/Instance.html

        # ドメインコントローラ用EC2ホスト
        local_domain_controller_windows = ec2.Instance(
            self, 'LocalDomainControllerWindows',
            instance_type=ec2.InstanceType('t3.large'),
            machine_image=ec2.WindowsImage(version=ec2.WindowsVersion.WINDOWS_SERVER_2012_R2_RTM_JAPANESE_64BIT_BASE),
            key_name=self.node.try_get_context('key_name'),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.ISOLATED),
            security_group=internal_sg
        )
        local_domain_controller_windows.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        # クライアント用EC2ホスト
        local_domain_client_windows = ec2.Instance(
            self, 'LocalDomainClientWindows',
            instance_type=ec2.InstanceType('t3.large'),
            machine_image=ec2.WindowsImage(version=ec2.WindowsVersion.WINDOWS_SERVER_2012_R2_RTM_JAPANESE_64BIT_BASE),
            key_name=self.node.try_get_context('key_name'),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.ISOLATED),
            security_group=internal_sg
        )
        local_domain_client_windows.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        self.output_props = props.copy()

    @property
    def outputs(self):
        return self.output_props
