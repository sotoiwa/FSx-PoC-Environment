from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_fsx as fsx
)


class AWSManagedADFSxStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']
        internal_sg = props['internal_sg']

        # AWS Managed ADに接続するFSx
        aws_managed_ad_fs = fsx.CfnFileSystem(
            self, 'AWSManagedADFileSystem',
            file_system_type='WINDOWS',
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids,
            security_group_ids=[internal_sg.security_group_id],
            storage_capacity=50,
            windows_configuration={
                "activeDirectoryId": self.node.try_get_context('aws_managed_ad')['directory_id'],
                "deploymentType": "MULTI_AZ_1",
                "preferredSubnetId": vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids[1],
                "throughputCapacity": 8
            }
        )

        self.output_props = props.copy()

    @property
    def outputs(self):
        return self.output_props
