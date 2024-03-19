#!/usr/bin/env python3
"""
signals.py
"""
from __future__ import print_function

import signal
import sys
import time

import harness
from harness import register, expect_prompt

#
# Test Cases
#
# TODO:
# - Fold code from demo/
#   - sigwinch-bug.sh -- invokes $OSH with different snippets, then manual window resize
#   - signal-during-read.sh -- bash_read and osh_read with manual kill -HUP $PID
#     trap handler HUP
#   - bug-858-trap.sh -- wait and kill -USR1 $PID
#     trap handler USR1
#     trap handler USR2
# - Fill out this TEST MATRIX.
#
# A. Which shell?  osh, bash, dash, etc.
#
# B. What mode is it in?
#
#    1. Interactive (stdin is a terminal)
#    2. Non-interactive
#
# C. What is the main thread of the shell doing?
#
#    1. waiting for external process: sleep 1
#    2. wait builtin:                 sleep 5 & wait
#       variants: wait -n: this matters when testing exit code
#    3. read builtin                  read
#       variants: FIVE kinds, read -d, read -n, etc.
#    4. computation, e.g. fibonacci with $(( a + b ))
#
# if interactive:
#    5. keyboard input from terminal with select()
#
#    Another way to categorize the main loop:
#    1. running script code
#    2. running trap code
#    3. running TAB completion plugin code
#
# D. What is it interrupted by?
#
#    1. SIGINT
#    2. SIGTSTP
#    3. SIGWINCH
#    4. SIGUSR1 -- doesn't this quit?
#
# if interactive:
#    1. SIGINT  Ctrl-C from terminal (relies on signal distribution to child?)
#    2. SIGTSTP Ctrl-Z from terminal
#
# E. What is the signal state?
#
#    1. no trap handlers installed
#    2. trap 'echo X' SIGWINCH
#    3. trap 'echo X' SIGINT ?


@register()
def sigusr1_trapped_prompt(sh):
    'Trapped SIGUSR1 while waiting at prompt (bug 1080)'

    # Notes on shell behavior:
    # bash and dash:
    # - If there are multiple USR1 signals, only one handler is run.
    # - The handlers aren't run in between PS1 and PS2.  There has to be another
    #   command.  So it's run in the InteractiveLoop and not the LineReader.
    # zsh and mksh:
    # - It's printed immediately!  You don't even have to hit ENTER.  That's
    #   probably because the line editor is integrated in both shells.
    # I think it's OK t match bash and dash.

    expect_prompt(sh)

    sh.sendline("trap 'echo zzz-USR1' USR1")
    expect_prompt(sh)

    sh.kill(signal.SIGUSR1)

    # send an empty line
    sh.sendline('')
    sh.expect('zzz-USR1')


@register()
def sigmultiple_trapped_prompt(sh):
    'Trapped USR1 and USR2 while waiting at prompt'

    expect_prompt(sh)

    sh.sendline("trap 'echo zzz-USR1' USR1")
    expect_prompt(sh)
    sh.sendline("trap 'echo zzz-USR2' USR2")
    expect_prompt(sh)

    sh.kill(signal.SIGUSR1)
    time.sleep(
        0.1)  # pause for a bit to avoid racing on signal order in osh-cpp
    sh.kill(signal.SIGUSR2)

    sh.sendline('echo hi')

    sh.expect('zzz-USR1')
    sh.expect('zzz-USR2')
    sh.sendline('hi')


@register()
def sighup_trapped_wait(sh):
    'trapped SIGHUP during wait builtin'

    sh.sendline("trap 'echo HUP' HUP")
    expect_prompt(sh)
    sh.sendline('sleep 1 &')
    # TODO: expect something like [1] 24370
    sh.sendline('wait')

    time.sleep(0.1)

    sh.kill(signal.SIGHUP)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=129')


@register()
def sigint_trapped_wait(sh):
    'trapped SIGINT during wait builtin'

    # This is different than Ctrl-C during wait builtin, because it's trapped!

    sh.sendline("trap 'echo INT' INT")
    sh.sendline('sleep 1 &')
    sh.sendline('wait')

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGINT)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


@register()
def ctrl_c_after_removing_sigint_trap(sh):
    'Ctrl-C after removing SIGINT trap (issue 1607)'

    sh.sendline('echo status=$?')
    sh.expect('status=0')

    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('trap - SIGINT')
    expect_prompt(sh)

    # Why do we need this?  Weird race condition
    # I would have thought expect_prompt() should be enough synchronization
    time.sleep(0.1)

    sh.sendintr()  # SIGINT
    expect_prompt(sh)

    # bash, zsh, mksh give status 130, dash and OSH gives 0
    #sh.sendline('echo status=$?')
    #sh.expect('status=130')

    sh.sendline('echo hi')
    sh.expect('hi')
    expect_prompt(sh)


@register()
def sigwinch_trapped_wait(sh):
    'trapped SIGWINCH during wait builtin'

    sh.sendline("trap 'echo WINCH' WINCH")
    sh.sendline('sleep 1 &')
    sh.sendline('wait')

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGWINCH)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=156')


@register()
def sigwinch_untrapped_wait(sh):
    'untrapped SIGWINCH during wait builtin (issue 1067)'

    sh.sendline('sleep 1 &')
    sh.sendline('wait')

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGWINCH)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=0')


# dash and mksh don't have pipestatus
@register(skip_shells=['dash', 'mksh'])
def sigwinch_untrapped_wait_n(sh):
    'untrapped SIGWINCH during wait -n'

    sh.sendline('sleep 1 &')
    sh.sendline('wait -n')

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGWINCH)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=0')


# dash and mksh don't have pipestatus
@register()
def sigwinch_untrapped_wait_pid(sh):
    'untrapped SIGWINCH during wait $!'

    sh.sendline('sleep 1 &')
    sh.sendline('wait $!')

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGWINCH)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=0')


@register()
def sigwinch_untrapped_external(sh):
    'untrapped SIGWINCH during external command'

    sh.sendline('sleep 0.5')  # slower than timeout

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGWINCH)

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=0')


# dash doesn't have pipestatus
@register(skip_shells=['dash'])
def sigwinch_untrapped_pipeline(sh):
    'untrapped SIGWINCH during pipeline'

    sh.sendline('sleep 0.5 | echo x')  # slower than timeout

    time.sleep(0.1)

    # simulate window size change
    sh.kill(signal.SIGWINCH)

    expect_prompt(sh)

    sh.sendline('echo pipestatus=${PIPESTATUS[@]}')
    sh.expect('pipestatus=0 0')


@register()
def t1(sh):
    'Ctrl-C during external command'

    sh.sendline('sleep 5')

    time.sleep(0.1)
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


@register(skip_shells=['mksh'])
def t4(sh):
    'Ctrl-C during pipeline'
    sh.sendline('sleep 5 | cat')

    time.sleep(0.1)
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


# TODO:
# - Expand this to call kinds of reads
#   - note that mksh only has some of them
# - Expand to trapped and untrapped
# - Expand to Ctrl-C vs. SIGWINCH


@register()
def t2(sh):
    'Ctrl-C during read builtin'

    sh.sendline('read myvar')

    time.sleep(0.1)
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


@register()
def read_d(sh):
    'Ctrl-C during read -d'

    sh.sendline('read -d :')

    time.sleep(0.1)
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


@register()
def c_wait(sh):
    'Ctrl-C (untrapped) during wait builtin'

    sh.sendline('sleep 5 &')
    sh.sendline('wait')

    time.sleep(0.1)

    # TODO: actually send Ctrl-C through the terminal, not SIGINT?
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


@register()
def c_wait_n(sh):
    'Ctrl-C (untrapped) during wait -n builtin'

    sh.sendline('sleep 5 &')
    sh.sendline('wait -n')

    time.sleep(0.1)

    # TODO: actually send Ctrl-C through the terminal, not SIGINT?
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    sh.expect('status=130')


@register()
def c_wait_line(sh):
    'Ctrl-C (untrapped) cancels entire interactive line'

    # the echo should be cancelled
    sh.sendline('sleep 10 & wait; echo status=$?')

    time.sleep(0.1)

    # TODO: actually send Ctrl-C through the terminal, not SIGINT?
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo done=$?')
    sh.expect('done=130')


@register()
def t5(sh):
    'Ctrl-C during Command Sub (issue 467)'
    sh.sendline('`sleep 5`')

    time.sleep(0.1)
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo status=$?')
    # TODO: This should be status 130 like bash
    sh.expect('status=130')


@register()
def loop_break(sh):
    'Ctrl-C (untrapped) exits loop'

    sh.sendline('while true; do continue; done')

    time.sleep(0.1)

    # TODO: actually send Ctrl-C through the terminal, not SIGINT?
    sh.sendintr()  # SIGINT

    expect_prompt(sh)

    sh.sendline('echo done=$?')
    sh.expect('done=130')


if __name__ == '__main__':
    try:
        sys.exit(harness.main(sys.argv))
    except RuntimeError as e:
        print('FATAL: %s' % e, file=sys.stderr)
        sys.exit(1)
