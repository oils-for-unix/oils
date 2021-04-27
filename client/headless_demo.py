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


# EVAL x
COMMANDS = [
  b'echo hi',          # OK, and prints 'hi' to stdout file descriptor
  b'echo !!',          # no history

  # Headless mode uses something like 'eval' to handle multiline commands
  b'echo one\necho two\necho three\n',  # multiline
  b'echo 1;\necho 2;\necho 3\n',        # with semicolons

  b'( \necho subshell\n)\n',            # proper multiline command

  b'ls --color=auto',  # OK, and make sure it's in color!
  b'read x',           # OK, and x is assigned
  b'echo "x: $x"',     # OK, we maintained state
  b'(',                # OK, syntax error to stderr  
  b'zzZZ',             # OK, and runtime error to stderr
  b'declare -X',       # OK, and runtime error to stderr
  b'echo PS1=${PS1@P}',   # typical prompt command
  b'echo $? $PWD',    # dump state.  TODO: JSON?

  # Errors at top level
  b'break',    
  b'continue',    

  # Hm this could actually return
  b'return',    
  b'exit',   # This exists the process
  b'echo done',    

  # What about async commands like &
  # I think that works the same?

  # Is this valid?  EVAL space?  I think it probably shouldn't be?
  b'',
  # What about invalid netstrings?
]


def ShowDescriptorState(label):
  if 1:
    pid = os.getpid()
    print(label + ' (PID %d)' % pid, file=sys.stderr)
    os.system('ls -l /proc/%d/fd >&2' % pid)


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

  opts, args = p.parse_args(argv[1:])

  # left: we read and write from it
  # right: the server we spawn reads and writes.
  left, right = socket.socketpair()

  ShowDescriptorState('parent/client BEFORE')

  # The server/child should inherit these descriptors
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

    import time
    time.sleep(0.1)  # prevent interleaving of parent/child state
    ShowDescriptorState('child/server')

    # never returns
    os.execv(child_argv[0], child_argv)
  else:
    right.close()  # close child end in parent

    ShowDescriptorState('parent/client AFTER')

  master_fd, slave_fd = -1, -1

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

  # Send raw requests, for testing protocol errors
  if args:
    raw_requests = [a.encode('utf-8') for a in args]

    status = 0
    for req in raw_requests:
      left.send(req)

      try:
        reply = py_fanos.recv(left)
      except ValueError as e:
        log('FANOS protocol error: %s', e)
        break

      log('reply %r' % reply)

      if reply.startswith(b'ERROR'):
        status = 1


      if reply is None:
        break
    return status

  # The normal path

  commands = [b'GETPID']
  #commands = [b'EVAL echo prompt ${PS1@P}']
  commands.extend(b'EVAL ' + c for c in COMMANDS)

  for cmd in commands:
    py_fanos.send(left, cmd, [stdin_fd, stdout_fd, stderr_fd])

    try:
      reply = py_fanos.recv(left)
    except ValueError as e:
      log('FANOS protocol error: %s', e)
      break

    log('reply %r' % reply)
    if reply is None:
      break

  left.close()

  if master_fd != -1:
    # This hangs because the server still has the terminal open?  Not sure
    # where to close it.
    while True:
      chunk = os.read(master_fd, 1024)
      if not chunk:
        break
      log('from pty: %r', chunk)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
