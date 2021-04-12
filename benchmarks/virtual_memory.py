#!/usr/bin/env python2
"""
virtual_memory.py
"""

import csv
import os
import sys
import re

# VmSize, VmData might be interesting too.
METRIC_RE = re.compile('^(VmPeak|VmRSS):\s*(\d+)')


def main(argv):
  action = argv[1]

  if action == 'baseline':
    input_dirs = argv[2:]

    out = csv.writer(sys.stdout)
    out.writerow(
        ('host', 'shell_name', 'shell_hash', 'metric_name', 'metric_value'))

    # Dir name looks like "$host.$job_id"
    for input_dir in input_dirs:
      d = os.path.basename(input_dir)
      host, job_id = d.split('.')
      for name in os.listdir(input_dir):
        n, _ = os.path.splitext(name)
        shell_name, shell_hash = n.split('-')
        path = os.path.join(input_dir, name)
        with open(path) as f:
          for line in f:
            m = METRIC_RE.match(line)
            if m:
              name, value = m.groups()
              row = (host, shell_name, shell_hash, name, value)
              out.writerow(row)

  elif action == 'osh-parser':
    input_dirs = argv[2:]
    out = csv.writer(sys.stdout)
    HEADER = (
        'host', 'shell_name', 'shell_hash', 'filename', 'metric_name',
        'metric_value')
    out.writerow(HEADER)

    for input_dir in input_dirs:
      d = os.path.basename(input_dir)
      host, job_id, _ = d.split('.')
      for name in os.listdir(input_dir):
        n, _ = os.path.splitext(name)
        shell_id, filename = n.split('__')
        shell_name, shell_hash = shell_id.split('-')

        path = os.path.join(input_dir, name)
        with open(path) as f:
          for line in f:
            m = METRIC_RE.match(line)
            if m:
              name, value = m.groups()
              row = (host, shell_name, shell_hash, filename, name, value)
              out.writerow(row)

  elif action == 'osh-runtime':
    # NOTE:  This is mostly a copy/paste of osh-parser.

    input_dirs = argv[2:]
    out = csv.writer(sys.stdout)
    HEADER = (
        'host', 'shell_name', 'shell_hash', 'task_arg', 'event', 'metric_name',
        'metric_value')
    out.writerow(HEADER)

    for input_dir in input_dirs:
      d = os.path.basename(input_dir)
      host, job_id, _ = d.split('.')
      for name in os.listdir(input_dir):
        n, _ = os.path.splitext(name)
        # NOTE: event used to be parser or runtime, but it's no longer used.
        # Code can probably be simplified.
        shell_id, task_arg, event = n.split('__')
        shell_name, shell_hash = shell_id.split('-')

        path = os.path.join(input_dir, name)
        with open(path) as f:
          for line in f:
            m = METRIC_RE.match(line)
            if m:
              name, value = m.groups()
              row = (host, shell_name, shell_hash, task_arg, event, name,
                  value)
              out.writerow(row)

  else:
    raise RuntimeError('Invalid action %r' % action)



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
