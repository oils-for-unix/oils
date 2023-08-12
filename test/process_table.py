#!/usr/bin/env python2
"""
Utility for checking the output of group-session.sh
"""
from __future__ import print_function

import re
import sys


class Process(object):

  def __init__(self, pid, ppid, pgid, comm):
    self.pid = pid
    self.ppid = ppid
    self.pgid = pgid
    self.comm = comm

  def __str__(self):
    return '\t'.join((self.pid, self.ppid, self.pgid, self.comm))

  def assert_pgid(self, pgid):
    if self.pgid != pgid:
      print('[%s] has pgid %s. expected %s.' %
          (self, self.pgid, pgid), file=sys.stderr)
      sys.exit(1)

class ProcessTree(object):

  def __init__(self, proc):
    self.proc = proc
    self.children = []
  
  def __str__(self):
    lines = [str(self.proc)]
    for child in self.children:
      lines.append(str(child))

    return '\n'.join(lines)

  def assert_child_count(self, n):
    if len(self.children) != n:
      print('[%s] has %d children. expected %d.' %
          (self.proc, len(self.children), n), file=sys.stderr)
      sys.exit(1)


def parse_process_tree(f, runner_pid):
  procs = {}

  for line in f:
    m = re.match(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(\w+)$', line)
    if not m:
      continue
    # TODO: use SID and TPGID
    pid, ppid, pgid, _, _, comm = m.groups()
    proc = Process(pid, ppid, pgid, comm)
    ptree = ProcessTree(proc)
    procs[proc.pid] = ptree
    if proc.ppid in procs:
      procs[proc.ppid].children.append(ptree)

  if runner_pid not in procs:
    print('malformed ps output', file=sys.stderr)
    sys.exit(1)

  # first process is the test harness
  root = procs[runner_pid]
  root.assert_child_count(1)
  return root.children[0]


def check_proc(ptree, shell, interactive):
  assert len(ptree.children) == 1
  ps = ptree.children[0]
  if interactive:
    ps.proc.assert_pgid(ps.proc.pid)
  else:
    ps.proc.assert_pgid(ptree.proc.pgid)


def check_pipe(ptree, shell, snippet, interactive):
  if snippet == 'fgpipe-lastpipe' and ('zsh' in shell or 'osh' in shell):
    expected_children = 2
  else:
    expected_children = 3

  ptree.assert_child_count(expected_children)

  first = None
  for child in ptree.children:
    if child.proc.pid == child.proc.pgid:
      first = child
      break

  if not first and interactive:
    print('interactive pipeline has no leader', file=sys.stderr) 
    sys.exit(1)

  pgid = first.proc.pgid if first else ptree.proc.pgid

  for child in ptree.children:
    child.proc.assert_pgid(pgid)


def check_subshell(ptree, shell, interactive):
  ptree.assert_child_count(1)
  subshell = ptree.children[0]
  subshell.assert_child_count(1)
  ps = subshell.children[0]

  if interactive:
    subshell.proc.assert_pgid(subshell.proc.pid)
    ps.proc.assert_pgid(subshell.proc.pid)
  else:
    subshell.proc.assert_pgid(ptree.proc.pgid)
    ps.proc.assert_pgid(ptree.proc.pgid)


def check_csub(ptree, shell, interactive):
  ptree.assert_child_count(1)
  ps = ptree.children[0]
  ps.proc.assert_pgid(ptree.proc.pgid)


def check_psub(ptree, shell, interactive):
  ps, cat, subshell = None, None, None
  if shell == 'bash':
    ptree.assert_child_count(2)
    for child in ptree.children:
      if len(child.children) == 1:
        subshell = child
        ps = child.children[0]
      elif len(child.children) == 0:
        cat = child
      else:
        print('[%s] has unexpected child [%s]' % (ptree.proc, child), file=sys.stderr)
        sys.exit(1)

    if not subshell:
      print('missing expected subshell', file=sys.stderr)
      sys.exit(1)
  else:
    ptree.assert_child_count(2)
    # NOTE: Ideally we would check the comm field of the children, but `ps` may
    # have run before some of them called exec(). Luckily we're only checkign
    # that both children are in their own group in this case, so we just
    # guess...
    ps = ptree.children[0]
    cat = ptree.children[1]

  if not ps:
    print('missing ps', file=sys.stderr)
    sys.exit(1)

  if not cat:
    print('missing cat', file=sys.stderr)
    sys.exit(1)
  

  if not interactive:
    ps.proc.assert_pgid(ptree.proc.pgid)
    cat.proc.assert_pgid(ptree.proc.pgid)
    if subshell:
      subshell.proc.assert_pgid(ptree.proc.pgid)
  else:
    if shell == 'bash':
      # bash is interesting
      subshell.proc.assert_pgid(ptree.proc.pid)
      ps.proc.assert_pgid(ptree.proc.pid)
      cat.proc.assert_pgid(cat.proc.pid)
    else:
      # osh and zsh put all children in their own group
      ps.proc.assert_pgid(ps.proc.pid)
      cat.proc.assert_pgid(cat.proc.pid)


def main(argv):
  runner_pid = argv[1]
  shell = argv[2]
  snippet = argv[3]
  interactive = (argv[4] == 'yes')

  ptree = parse_process_tree(sys.stdin, runner_pid)
  if snippet == 'fgproc':
    check_proc(ptree, shell, interactive)

  elif snippet == 'bgproc':
    check_proc(ptree, shell, interactive)

  elif snippet == 'fgpipe':
    check_pipe(ptree, shell, snippet, interactive)

  elif snippet == 'fgpipe-lastpipe':
    check_pipe(ptree, shell, snippet, interactive)

  elif snippet == 'bgpipe':
    check_pipe(ptree, shell, snippet, interactive)

  elif snippet == 'bgpipe-lastpipe':
    check_pipe(ptree, shell, snippet, interactive)

  elif snippet == 'subshell':
    check_subshell(ptree, shell, interactive)

  elif snippet == 'csub':
    check_csub(ptree, shell, interactive)

  elif snippet == 'psub':
    check_psub(ptree, shell, interactive)

  else:
    raise RuntimeError('Invalid snippet %r' % snippet)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
