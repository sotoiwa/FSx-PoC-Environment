#!/usr/bin/env python3

from aws_cdk import core

from cdksample.network_stack import NetworkStack
from cdksample.bastion_stack import BastionStack
from cdksample.self_managed_ad_stack import SelfManagedADStack
from cdksample.aws_managed_ad_stack import AWSManagedADStack
from cdksample.self_managed_ad_fsx_stack import SelfManagedADFSxStack
from cdksample.aws_managed_ad_fsx_stack import AWSManagedADFSxStack


app = core.App()
prefix = app.node.try_get_context('stack_prefix')
env = core.Environment(
    account=app.node.try_get_context('account'),
    region=app.node.try_get_context('region')
)
props = dict()

network_stack = NetworkStack(app, '{}NetworkStack'.format(prefix), env=env, props=props)
props = network_stack.outputs

bastion_windows_stack = BastionStack(app, '{}BastionStack'.format(prefix), env=env, props=props)
props = bastion_windows_stack.outputs

self_managed_ad_stack = SelfManagedADStack(app, '{}SelfManagedADStack'.format(prefix), env=env, props=props)
props = self_managed_ad_stack.outputs

aws_managed_ad_stack = AWSManagedADStack(app, '{}AWSManagedADStack'.format(prefix), env=env, props=props)
props = aws_managed_ad_stack.outputs

local_domain_fsx_stack = SelfManagedADFSxStack(app, '{}SelfManagedADFSxStack'.format(prefix), env=env, props=props)
props = local_domain_fsx_stack.outputs

aws_managed_ad_fsx_stack = AWSManagedADFSxStack(app, '{}AWSManagedADFSxStack'.format(prefix), env=env, props=props)
props = aws_managed_ad_fsx_stack.outputs

app.synth()
