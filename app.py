#!/usr/bin/env python3

from aws_cdk import core

from cdksample.network_stack import NetworkStack
from cdksample.iam_stack import IamStack
from cdksample.bastion_windows_stack import BastionWindowsStack
from cdksample.microsoft_ad_stack import MicrosoftADStack
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

iam_stack = IamStack(app, '{}-IamStack'.format(prefix), env=env, props=props)
props = iam_stack.outputs

bastion_windows_stack = BastionWindowsStack(app, '{}-BastionWindowsStack'.format(prefix), env=env, props=props)
props = bastion_windows_stack.outputs

micorsoft_ad_stack = MicrosoftADStack(app, '{}-MicrosoftADStack'.format(prefix), env=env, props=props)
props = micorsoft_ad_stack.outputs

fsx_stack = FSxStack(app, '{}-FSxStack'.format(prefix), env=env, props=props)
props = fsx_stack.outputs

app.synth()
