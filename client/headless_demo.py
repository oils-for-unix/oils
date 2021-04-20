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
  'echo hi',     # OK, and prints 'hi' to stdout file descriptor
  'read x',      # OK, and x is assigned
  '(',           # OKK, syntax error to stderr  
  'zzZZ',        # OK, and runtime error to stderr
  'declare -X',  # OK, and runtime error to stderr

  # Is this valid?  ECMD space?  I think it probably shouldn't be?
  '',
  # What about invalid netstrings?
]


def ShowDescriptorState(label):
  if 1:
    pid = os.getpid()
    print(label + ' (PID %d)' % pid, file=sys.stderr)
    os.system('ls -l /proc/%d/fd >&2' % pid)


def main(argv):
  p = optparse.OptionParser(__doc__)

  p.add_option(
      '--to-file', dest='to_file', default=None,
      help='Where the server should send child stdout')
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
    msg = b'GETPID'

    if opts.to_file:
      stdout_fd = os.open(opts.to_file, os.O_RDWR | os.O_CREAT)

    elif opts.to_new_pty:
      master_fd, slave_fd = os.openpty()
      stdout_fd = slave_fd
      log('master %d slave %d', master_fd, slave_fd)
      #os.close(slave_fd)

    else:
      raise AssertionError()

    log('stdout_fd = %d', stdout_fd)

    # Send 2 messages across one connection
    for i in range(2):
      py_fanos.send(left, msg, [stdout_fd])

      reply = py_fanos.recv(left)
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
