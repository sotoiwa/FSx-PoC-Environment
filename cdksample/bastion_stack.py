from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_iam as iam
)


class BastionStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']
        internal_sg = props['internal_sg']
        bastion_sg = props['bastion_sg']

        # Bastion用EC2ホスト
        bastion_windows = ec2.Instance(
            self, 'Bastion',
            instance_type=ec2.InstanceType('t3.large'),
            machine_image=ec2.MachineImage.latest_windows(
                version=ec2.WindowsVersion.WINDOWS_SERVER_2016_JAPANESE_FULL_BASE),
            key_name=self.node.try_get_context('key_name'),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=internal_sg
        )
        bastion_windows.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))
        bastion_windows.add_security_group(bastion_sg)

        self.output_props = props.copy()

    @property
    def outputs(self):
        return self.output_props
