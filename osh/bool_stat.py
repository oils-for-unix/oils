#!/usr/bin/env python2
"""
bool_stat.py

Not translating this file directly.
"""
from __future__ import print_function

import stat
import posix_ as posix
from posix_ import X_OK, R_OK, W_OK  # refers directly to C macro
from _devbuild.gen.id_kind_asdl import Id, Id_t
from _devbuild.gen.syntax_asdl import word_t, loc
from core.pyerror import e_die
from core import ui


def isatty(fd_str, blame_word):
  # type: (str, word_t) -> bool
  try:
    fd = int(fd_str)
  except ValueError:
    e_die('Invalid file descriptor %r' % fd_str, loc.Word(blame_word))

  try:
    return posix.isatty(fd)
  # fd is user input, and causes this exception in the binding.
  except OverflowError:
    e_die('File descriptor %r is too big' % fd_str, loc.Word(blame_word))


def DoUnaryOp(op_id, s):
  # type: (Id_t, str) -> bool

  # Only use lstat if we're testing for a symlink.
  if op_id in (Id.BoolUnary_h, Id.BoolUnary_L):
    try:
      mode = posix.lstat(s).st_mode
    except OSError:
      # TODO: simple_test_builtin should this as status=2.
      #e_die("lstat() error: %s", e, word=node.child)
      return False

    return stat.S_ISLNK(mode)

  try:
    st = posix.stat(s)
  except OSError as e:
    # TODO: simple_test_builtin should this as status=2.
    # Problem: we really need errno, because test -f / is bad argument,
    # while test -f /nonexistent is a good argument but failed.  Gah.
    # ENOENT vs. ENAMETOOLONG.
    #e_die("stat() error: %s", e, word=node.child)
    return False
  mode = st.st_mode

  if op_id in (Id.BoolUnary_e, Id.BoolUnary_a):  # -a is alias for -e
    return True

  if op_id == Id.BoolUnary_f:
    return stat.S_ISREG(mode)

  if op_id == Id.BoolUnary_d:
    return stat.S_ISDIR(mode)

  if op_id == Id.BoolUnary_b:
    return stat.S_ISBLK(mode)

  if op_id == Id.BoolUnary_c:
    return stat.S_ISCHR(mode)

  if op_id == Id.BoolUnary_k:
    # need 'bool' for MyPy
    return bool(stat.S_IMODE(mode) & stat.S_ISVTX)

  if op_id == Id.BoolUnary_p:
    return stat.S_ISFIFO(mode)

  if op_id == Id.BoolUnary_S:
    return stat.S_ISSOCK(mode)

  if op_id == Id.BoolUnary_x:
    return posix.access(s, X_OK)

  if op_id == Id.BoolUnary_r:
    return posix.access(s, R_OK)

  if op_id == Id.BoolUnary_w:
    return posix.access(s, W_OK)

  if op_id == Id.BoolUnary_s:
    return st.st_size != 0

  if op_id == Id.BoolUnary_u:
    return bool(stat.S_IMODE(mode) & stat.S_ISUID)

  if op_id == Id.BoolUnary_g:
    return bool(stat.S_IMODE(mode) & stat.S_ISGID)

  if op_id == Id.BoolUnary_O:
    return st.st_uid == posix.geteuid()

  if op_id == Id.BoolUnary_G:
    return st.st_gid == posix.getegid()

  # implicit location
  e_die("%s isn't implemented" % ui.PrettyId(op_id), loc.Missing())


def DoBinaryOp(op_id, s1, s2):
  # type: (Id_t, str, str) -> bool
  try:
    st1 = posix.stat(s1)
  except OSError:
    st1 = None
  try:
    st2 = posix.stat(s2)
  except OSError:
    st2 = None

  if op_id in (Id.BoolBinary_nt, Id.BoolBinary_ot):
    # pretend it's a very old file
    m1 = 0 if st1 is None else st1.st_mtime
    m2 = 0 if st2 is None else st2.st_mtime
    if op_id == Id.BoolBinary_nt:
      return m1 > m2
    else:
      return m1 < m2

  if op_id == Id.BoolBinary_ef:
    if st1 is None:
      return False
    if st2 is None:
      return False
    return st1.st_dev == st2.st_dev and st1.st_ino == st2.st_ino

  raise AssertionError(op_id)
