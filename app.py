#!/usr/bin/env python3

from aws_cdk import core

from cdksample.network_stack import NetworkStack
from cdksample.bastion_stack import BastionStack
from cdksample.resource_domain_stack import ResourceDomainStack
from cdksample.japan_domain_stack import JapanDomainStack
from cdksample.resource_domain_fsx_stack import ResourceDomainFSxStack

app = core.App()
prefix = app.node.try_get_context('stack_prefix')
env = core.Environment(
    account=app.node.try_get_context('account'),
    region=app.node.try_get_context('region')
)
props = dict()

network_stack = NetworkStack(app, '{}-NetworkStack'.format(prefix), env=env, props=props)
props = network_stack.outputs

bastion_windows_stack = BastionStack(app, '{}-BastionStack'.format(prefix), env=env, props=props)
props = bastion_windows_stack.outputs

resource_domain_stack = ResourceDomainStack(app, '{}-ResourceDomainStack'.format(prefix), env=env, props=props)
props = resource_domain_stack.outputs

japan_domain_stack = JapanDomainStack(app, '{}-JapanDomainStack'.format(prefix), env=env, props=props)
props = japan_domain_stack.outputs

resource_domain_fsx_stack = ResourceDomainFSxStack(app, '{}-ResourceDomainFSxStack'.format(prefix), env=env, props=props)
props = resource_domain_fsx_stack.outputs

app.synth()
