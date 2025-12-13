#!/usr/bin/env python3
"""
Test history expansion

To invoke this file, run the shell wrapper:

    test/stateful.sh history-quick
"""
from __future__ import print_function

import sys

import harness
from harness import expect_prompt, register

from test.spec_lib import log


@register()
def history_bangbang(sh):
    """test basic !! expansion - previous command"""
    expect_prompt(sh)

    sh.sendline('echo 11')
    sh.expect('11')

    sh.sendline('echo 22')
    sh.expect('22')

    sh.sendline('echo !!')
    sh.expect('echo 22')


@register(not_impl_shells=['bash'])
def history_bangbang(sh):
    """Inside double quotes, !! should not be expanded, unlike bash """
    expect_prompt(sh)

    sh.sendline('echo 33')
    sh.expect('33')

    sh.sendline('echo "!!"')
    sh.expect('!!')


if __name__ == '__main__':
    try:
        sys.exit(harness.main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
