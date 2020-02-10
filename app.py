#!/usr/bin/env python3

from aws_cdk import core

from cdksample.network_stack import NetworkStack
from cdksample.bastion_stack import BastionStack
from cdksample.local_domain_stack import LocalDomainStack
from cdksample.managed_ad_stack import ManagedADStack
from cdksample.fsx_stack import FSxStack


app = core.App()
prefix = app.node.try_get_context('stack_prefix')
env = core.Environment(
    account=app.node.try_get_context('account'),
    region=app.node.try_get_context('region')
)
props = dict()

network_stack = NetworkStack(app, '{}-NetworkStack'.format(prefix), env=env, props=props)
props = network_stack.outputs

local_domain_stack = LocalDomainStack(app, '{}-LocalDomainStack'.format(prefix), env=env, props=props)
props = local_domain_stack.outputs

bastion_windows_stack = BastionStack(app, '{}-BastionStack'.format(prefix), env=env, props=props)
props = bastion_windows_stack.outputs

managed_ad_stack = ManagedADStack(app, '{}-ManagedADStack'.format(prefix), env=env, props=props)
props = managed_ad_stack.outputs

fsx_stack = FSxStack(app, '{}-FSxStack'.format(prefix), env=env, props=props)
props = fsx_stack.outputs

app.synth()
