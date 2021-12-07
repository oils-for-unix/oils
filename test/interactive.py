#! /usr/bin/python2

import pexpect
import re
import signal
import sys
import os


SHELL = os.environ.get("OSH_TEST_INTERACTIVE_SHELL", "bin/osh")
DEBUG = "OSH_TEST_INTERACTIVE_DEBUG" in os.environ
TIMEOUT = int(os.environ.get("OSH_TEST_INTERACTIVE_TIMEOUT", 2))

global g_failures
g_failures = 0


def get_pid_by_name(name):
    """Return the pid of the process matching `name`."""
    # XXX: make sure this is restricted to subprocesses under us.
    return int(pexpect.run("pgrep cat").split()[-1])


# XXX: osh.sendcontrol("z") does not suspend the foreground process :(
#
# why does osh.sendcontrol("c") generate SIGINT, while osh.sendcontrol("z")
# appears to do nothing?
def stop_process__hack(name):
    """Send sigstop to the most recent process matching `name`"""
    os.kill(get_pid_by_name(name), signal.SIGSTOP)


def kill_process(name):
    """Kill the most recent process matching `name`."""
    os.kill(get_pid_by_name(name), signal.SIGINT)


class InteractiveTest(object):
    """Define a test case for the interactive shell.

    This is implemented as a context-manager wrapper around
    pexpect.spawn, used like:

    with InteractiveTest(....) as osh:
       osh.sendline(...)
       osh.expect(...)
       ...
    """

    def __init__(self, description, cmdline=SHELL):
        self.cmdline = cmdline
        self.shell = None
        self.description = description

    def __enter__(self):
        if DEBUG:
            print self.description
        else:
            # note, trailing comma to suppress newline.
            print self.description,

        self.shell = pexpect.spawn(self.cmdline, timeout=TIMEOUT)

        # suppress output when DEBUG is not set.
        if DEBUG:
            self.shell.logfile = sys.stdout

        # generally don't want local echo, it gets confusing fast.
        self.shell.setecho(False)
        return self.shell

    def __exit__(self, t, v, tb):
        global g_failures
        self.shell.close()

        if not DEBUG:
            # show result of test
            if tb:
                g_failures += 1
                print "... Fail"
            else:
                print "... OK"
            # Allow other tests to keep running
            return True
        else:
            # Fail fast when in debug mode.
            pass


### Test Cases Below ##########################################################


with InteractiveTest("Regression test for issue #1004") as osh:
    osh.expect(r'.*\$ ')
    osh.sendline("cat")
    stop_process__hack("cat")
    osh.expect("\r\n\\[PID \\d+\\] Stopped")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect(r"Continue PID \d+")
    osh.sendcontrol("c")
    osh.expect(r"JobState NotifyDone \d+")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")


with InteractiveTest("Test resuming a killed process") as osh:
    osh.expect(r'.*\$ ')
    osh.sendline("cat")
    stop_process__hack("cat")
    osh.expect("\r\n\\[PID \\d+\\] Stopped")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect(r"Continue PID \d+")
    kill_process("cat")
    osh.expect(r"JobState NotifyDone \d+")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")


with InteractiveTest("Regression test for issue #721") as osh:
    osh.expect(r".*\$")
    osh.sendline("cat")
    osh.sendcontrol("c")
    # Osh does not print in this case, not sure why...
    # osh.expect(r"\r\nJobState NotifyDone \d+")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")
    osh.expect(r".*\$")


### Don't touch this ##########################################################

exit(g_failures)
