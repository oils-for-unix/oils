#!/usr/bin/env python3
"""
Interactively tests shell bindings.

To invoke this file, run the shell wrapper:

    test/stateful.sh bind-quick
"""
from __future__ import print_function

import sys
import time

import harness
from harness import expect_prompt, register

from test.spec_lib import log


def add_foo_fn(sh):
    sh.sendline('function foo() { echo "FOO"; }')
    time.sleep(0.1)


def send_bind(sh, opts, keymap=None):
    "Helper method to send a bind command and sleep for a moment. W/ optional keymap."

    if keymap:
        sh.sendline(f"bind -m {keymap} {opts}")
    else:
        sh.sendline(f"bind {opts}")
    time.sleep(0.1)


@register(not_impl_shells=['dash', 'mksh'])
def bind_plain(sh):
    "test bind (w/out flags) for adding bindings to readline fns"
    expect_prompt(sh)

    # There aren't many readline fns that will work nicely with pexpect (e.g., cursor-based fns)
    # Editing input seems like a reasonable choice
    send_bind(sh, ''' '"\C-x\C-h": backward-delete-char' ''')
    expect_prompt(sh)

    sh.send("echo FOOM")
    sh.sendcontrol('x')
    sh.sendcontrol('h')
    sh.sendline("P")
    time.sleep(0.1)

    sh.expect("FOOP")


@register(not_impl_shells=['dash', 'mksh'])
def bind_r_for_bind_x_osh_fn(sh):
    """
    test bind -r for removing bindings to arbitrary cmds made with bind -x
    (regular readline fn bind removal is tested in noninteractive builtin-bind.test.sh)
    """
    expect_prompt(sh)

    add_foo_fn(sh)
    expect_prompt(sh)

    send_bind(sh, """-x '"\C-x\C-f": foo' """)
    expect_prompt(sh)

    sh.sendcontrol('x')
    sh.sendcontrol('f')
    time.sleep(0.1)
    sh.expect("FOO")

    send_bind(sh, '-r "\C-x\C-f" ')

    sh.sendcontrol('x')
    sh.sendcontrol('f')
    time.sleep(0.1)

    expect_prompt(sh)


@register(not_impl_shells=['dash', 'mksh'])
def bind_x(sh):
    "test bind -x for setting bindings to custom shell functions"
    expect_prompt(sh)

    add_foo_fn(sh)
    expect_prompt(sh)

    send_bind(sh, """-x '"\C-x\C-f": foo' """)
    expect_prompt(sh)

    sh.sendcontrol('x')
    sh.sendcontrol('f')
    time.sleep(0.1)

    sh.expect("FOO")


@register(not_impl_shells=['dash', 'mksh'])
def bind_x_runtime_envvar_vals(sh):
    "test bind -x for using env var runtime values (e.g., 'echo $PWD' should change with dir)"
    expect_prompt(sh)

    sh.sendline("export BIND_X_VAR=foo")

    send_bind(sh, """-x '"\C-x\C-f": echo $BIND_X_VAR' """)
    expect_prompt(sh)

    sh.sendline("export BIND_X_VAR=bar")
    expect_prompt(sh)

    sh.sendcontrol('x')
    sh.sendcontrol('f')
    time.sleep(0.1)

    sh.expect("bar")


@register(not_impl_shells=['dash', 'mksh'])
def bind_x_readline_line(sh):
    "test bind -x for correctly setting $READLINE_LINE for the cmd"
    expect_prompt(sh)

    send_bind(sh, """-x '"\C-x\C-f": echo Current line is: $READLINE_LINE' """)
    expect_prompt(sh)

    sh.send('abcdefghijklmnopqrstuvwxyz')

    sh.sendcontrol('x')
    sh.sendcontrol('f')
    time.sleep(0.1)

    # must not match any other output (like debug output or shell names)
    sh.expect("Current line is: abcdefghijklmnopqrstuvwxyz")

    sh.sendline(
        '[[ -v READLINE_LINE ]] && echo "READLINE_LINE is set" || echo "READLINE_LINE is unset"'
    )
    sh.expect("READLINE_LINE is unset")


@register(not_impl_shells=['dash', 'mksh'])
def bind_x_readline_point(sh):
    "test bind -x for correctly setting $READLINE_POINT for the cmd"
    cmd_str = 'abcdefghijklmnop'
    expected_rl_point = len(cmd_str)

    expect_prompt(sh)

    send_bind(sh,
              """-x '"\C-x\C-f": echo Cursor point at: $READLINE_POINT' """)
    expect_prompt(sh)

    sh.send(cmd_str)

    sh.sendcontrol('x')
    sh.sendcontrol('f')
    time.sleep(0.1)

    sh.expect("Cursor point at: " + str(expected_rl_point))

    sh.sendline(
        '[[ -v READLINE_POINT ]] && echo "READLINE_POINT is set" || echo "READLINE_POINT is unset"'
    )
    sh.expect("READLINE_POINT is unset")


@register(not_impl_shells=['dash', 'mksh'])
def bind_u(sh):
    "test bind -u for unsetting all bindings to a fn"
    expect_prompt(sh)

    send_bind(sh, "'\C-p: yank'")
    expect_prompt(sh)

    send_bind(sh, "-u yank")
    expect_prompt(sh)

    send_bind(sh, "-q yank")
    sh.expect("yank is not bound to any keys")


@register(not_impl_shells=['dash', 'mksh'])
def bind_q(sh):
    "test bind -q for querying bindings to a fn"
    expect_prompt(sh)

    # Probably bound, but we're not testing that precisely
    send_bind(sh, "-q yank")
    sh.expect(["yank can be invoked via", "yank is not bound to any keys"])

    expect_prompt(sh)

    # Probably NOT bound, but we're not testing that precisely
    send_bind(sh, "-q dump-functions")
    sh.expect([
        "dump-functions can be invoked via",
        "dump-functions is not bound to any keys"
    ])


@register(not_impl_shells=['dash', 'mksh'])
def bind_m(sh):
    "test bind -m for setting bindings in specific keymaps"
    expect_prompt(sh)

    send_bind(sh, "-u yank", "vi")
    expect_prompt(sh)

    send_bind(sh, "'\C-p: yank'", "emacs")
    expect_prompt(sh)

    send_bind(sh, "-q yank", "vi")
    sh.expect("yank is not bound to any keys")
    expect_prompt(sh)

    send_bind(sh, "-q yank", "emacs")
    sh.expect("yank can be invoked via")


@register(not_impl_shells=['dash', 'mksh'])
def bind_f(sh):
    "test bind -f for setting bindings from an inputrc init file"
    expect_prompt(sh)

    send_bind(sh, "-f spec/testdata/bind/bind_f.inputrc")
    expect_prompt(sh)

    send_bind(sh, "-q downcase-word")
    sh.expect('downcase-word can be invoked via.*"\\\C-o\\\C-s\\\C-h"')


if __name__ == '__main__':
    try:
        sys.exit(harness.main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
