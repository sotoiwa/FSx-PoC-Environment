from aws_cdk import (
    core,
    aws_iam as iam
)


class IamStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ################
        # IAMロールの作成
        ################

        # 踏み台Windows用IAMロール
        bastion_windows_role = iam.Role(
            self, 'BastionWindowsRole',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com')
        )
        bastion_windows_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'))

        self.output_props = props.copy()
        self.output_props['bastion_windows_role'] = bastion_windows_role

    @property
    def outputs(self):
        return self.output_props
