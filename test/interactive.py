#! /usr/bin/python2

import pexpect
import re
import signal
import sys
import os

SHELL = "bin/osh"
DEBUG = True

def get_pid_by_name(name):
    # XXX: make sure this is restricted this to subprocesses under us.
    return int(pexpect.run("pgrep cat").split()[-1])

def stop_process__hack(name):
    # calling osh.sendcontrol("z") does not suspend the foreground process :(
    # find the process running under us one and send SIGSTOP directly.
    os.kill(get_pid_by_name(name), signal.SIGSTOP)

def kill_process__hack(name):
    os.kill(get_pid_by_name(name), signal.SIGINT)


# Context manager wrapper around pexpect.spawn
class TestShell(object):

    def __init__(self, cmdline):
        self.cmdline = cmdline
        self.shell = None

    def __enter__(self):
        self.shell = pexpect.spawn(self.cmdline, timeout=2)
        if DEBUG:
            self.shell.logfile = sys.stdout
        self.shell.setecho(False)
        return self.shell

    def __exit__(self, *dont_care):
        self.shell.close()


# Reproduce the bug as described in issue #1004
with TestShell(SHELL) as osh:
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


# Similar to above, but kill the process directly
with TestShell(SHELL) as osh:
    osh.expect(r'.*\$ ')
    osh.sendline("cat")
    stop_process__hack("cat")
    osh.expect("\r\n\\[PID \\d+\\] Stopped")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect(r"Continue PID \d+")
    kill_process__hack("cat")
    osh.expect(r"JobState NotifyDone \d+")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")


# Reproduce the bug as described in 721
with TestShell(SHELL) as osh:
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
