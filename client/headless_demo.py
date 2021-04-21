#!/usr/bin/env python3
"""
headless_demo.py

We're using Python 3 because it supports descriptor passing.

Steps:

- Create socketpair() for communication between 2 processes
- fork() and exec() osh --headless.
- Communicate synchronously
"""
import optparse
import os
import pty
import socket
import sys

import py_fanos
from py_fanos import log


# ECMD x
COMMANDS = [
  b'echo hi',     # OK, and prints 'hi' to stdout file descriptor
  b'read x',      # OK, and x is assigned
  b'(',           # OKK, syntax error to stderr  
  b'zzZZ',        # OK, and runtime error to stderr
  b'declare -X',  # OK, and runtime error to stderr

  # What about async commands like &
  # I think that works the same?

  # Is this valid?  ECMD space?  I think it probably shouldn't be?
  b'',
  # What about invalid netstrings?
]


def ShowDescriptorState(label):
  if 1:
    import time
    time.sleep(0.01)  # prevent interleaving

    pid = os.getpid()
    print(label + ' (PID %d)' % pid, file=sys.stderr)
    os.system('ls -l /proc/%d/fd >&2' % pid)

    time.sleep(0.01)  # prevent interleaving


def main(argv):
  p = optparse.OptionParser(__doc__)

  # By default, the server will use the stdin/stdout/stderr of THIS CLIENT
  # PROCESS.
  p.add_option(
      '--stdin-file', dest='stdin_file', default='/dev/stdin',
      help='Where the server read stdin from')
  p.add_option(
      '--stdout-file', dest='stdout_file', default='/dev/stdout',
      help='Where the server should send child stdout')
  p.add_option(
      '--stderr-file', dest='stderr_file', default='/dev/stderr',
      help='Where the server should send child stdout')

  # Use a terminal instead
  p.add_option(
      '--to-new-pty', dest='to_new_pty', default=False, action='store_true',
      help='Send the child stdout to a new PTY')

  opts, _ = p.parse_args(argv[1:])

  # FORK THE SERVER and pass it a socket.

  # left -> coprocess stdin
  # right -> coprocess stdout
  left, right = socket.socketpair()

  ShowDescriptorState('parent/client BEFORE')

  # This is necessary so that the child gets it
  os.set_inheritable(left.fileno(), True)
  os.set_inheritable(right.fileno(), True)

  child_argv = ['bin/osh', '--headless']

  ret = os.fork()
  if ret < 0:
    raise AssertionError('fork failed')

  elif ret == 0:
    left.close()  # close parent end in child

    # osh --headless will read from stdin, and write to stdout, which are both
    # the RIGHT socket.
    os.dup2(right.fileno(), 0)
    os.dup2(right.fileno(), 1)
    right.close()  # we don't need this either

    ShowDescriptorState('child/server')

    # never returns
    os.execv(child_argv[0], child_argv)
  else:
    right.close()  # close child end in parent

    ShowDescriptorState('parent/client AFTER')

  master_fd, slave_fd = -1, -1
  try:
    stdin_fd = os.open('/dev/stdin', 0)
    stderr_fd = os.open('/dev/stderr', 0)

    if opts.to_new_pty:
      master_fd, slave_fd = os.openpty()

      stdin_fd = slave_fd
      stdout_fd = slave_fd
      stderr_fd = slave_fd

      log('master %d slave %d', master_fd, slave_fd)
      #os.close(slave_fd)

    else:
      stdin_fd = os.open(opts.stdin_file, 0)
      stdout_fd = os.open(opts.stdout_file, os.O_RDWR | os.O_CREAT)
      stderr_fd = os.open(opts.stderr_file, os.O_RDWR | os.O_CREAT)

    log('stdout_fd = %d', stdout_fd)

    commands = [b'GETPID']
    commands.extend(b'ECMD ' + c for c in COMMANDS)

    for cmd in commands:
      py_fanos.send(left, cmd, [stdin_fd, stdout_fd, stderr_fd])

      try:
        reply = py_fanos.recv(left)
      except ValueError as e:
        log('FANOS protocol error: %s', e)
        break

      print('reply %r' % reply)
      if reply is None:
        break

  finally:
    log('closing socket')
    left.close()

  if master_fd != -1:
    # This hangs because the server still has the terminal open?  Not sure
    # where to close it.
    while True:
      chunk = os.read(master_fd, 1024)
      if not chunk:
        break
      log('from pty: %r', chunk)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
