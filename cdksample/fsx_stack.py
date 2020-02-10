from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_fsx as fsx
)


class FSxStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        vpc = props['vpc']
        internal_sg = props['internal_sg']
        managed_ad = props['managed_ad']

        # FSxその1
        fs1 = fsx.CfnFileSystem(
            self, 'FileSystem1',
            file_system_type='WINDOWS',
            subnet_ids=vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids,
            security_group_ids=[internal_sg.security_group_id],
            storage_capacity=100,
            windows_configuration={
                "activeDirectoryId": managed_ad.ref,
                "deploymentType": "MULTI_AZ_1",
                "preferredSubnetId": vpc.select_subnets(subnet_type=ec2.SubnetType.ISOLATED).subnet_ids[0],
                "throughputCapacity": 8
            }
        )

        self.output_props = props.copy()

    @property
    def outputs(self):
        return self.output_props