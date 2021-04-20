"""
py_fanos.py: Pure Python implementation of FANOS

Python 2 doesn't have native FD passing, but Python 3 does.
"""

import array
import socket
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def send(sock, msg, fds=None):
  """Send a blob and optional file descriptors."""

  fds = fds or []

  sock.send(b'%d:' % len(msg))  # netstring prefix

  # Send the FILE DESCRIPTOR with the NETSTRING PAYLOAD
  ancillary = (
    socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array("i", fds)
  )
  result = sock.sendmsg([msg], [ancillary])
  #log('sendmsg returned %s', result)

  sock.send(b',')  # trailing netstring thing


def recv_fds_once(sock, msglen, maxfds, fd_out):
  """Helper function from Python stdlib docs."""
  fds = array.array("i")   # Array of ints
  msg, ancdata, flags, addr = sock.recvmsg(msglen,
                                           socket.CMSG_LEN(maxfds * fds.itemsize))
  for cmsg_level, cmsg_type, cmsg_data in ancdata:
    if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
      # Append data, ignoring any truncated integers at the end.
      fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])

  fd_out.extend(fds)
  return msg


def recv(sock, fd_out=None):
  """Receive a blob and optional file descriptors.

  Returns:
    The message blob, or None when the other end closes at a valid message
    boundary.

    Appends to fd_out.
  """
  if fd_out is None:
    fd_out = []  # Can be thrown away

  len_buf = []
  for i in range(10):
    byte = sock.recv(1)
    #log('byte = %r', byte)

    # This happens on close()
    if len(byte) == 0:
      if i == 0:
        return None  # that was the last message
      else:
        raise ValueError('Unexpected EOF')

    if b'0' <= byte and byte <= b'9':
      len_buf.append(byte)
    else:
      break

  if len(len_buf) == 0:
    raise ValueError('Expected netstring length')
  if byte != b':':
    raise ValueError('Expected : after length')

  num_bytes = int(b''.join(len_buf))
  #log('num_bytes = %d', num_bytes)

  msg = b''
  while True:
    chunk = recv_fds_once(sock, num_bytes, 3, fd_out)
    #log("chunk %r  FDs %s", chunk, fds)

    msg += chunk
    if len(msg) == num_bytes:
      break

  byte = sock.recv(1)
  if byte != b',':
    raise ValueError('Expected ,')

  return msg
