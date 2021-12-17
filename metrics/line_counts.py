#!/usr/bin/env python2
"""
wc_html.py

Filter for HTML
"""
from __future__ import print_function

import os
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def main(argv):

  id_ = argv[1]
  title = argv[2]
  comment = argv[3]
  tmp_dir = argv[4]

  #log('ARGV %s ', argv)
  #log('PREFIX %s ', prefix)

  total_lines = None
  rows = []

  # Parse
  num_files = 0
  for line in sys.stdin:
    line = line.strip()
    count, rel_path = line.split(None, 1)
    count = int(count)

    if rel_path == 'total':
      total_lines = count
    else:
      rows.append((count, rel_path))
    num_files += 1

  # Append to row
  index_tsv = os.path.join(tmp_dir, 'INDEX.tsv')

  anchor = 'i%s' % id_

  record = {
      'id': id_,
      'total_lines': total_lines,
      'num_files': num_files,
      'title': title,
      'anchor': anchor,
      'comment': comment,
  }

  with open(index_tsv, 'a') as f:
    # The link looks like #i01
    f.write('%(title)s\t#%(anchor)s\t%(total_lines)d\t%(num_files)s\n' % record)

  # Write our HTML
  html = os.path.join(tmp_dir, '%02d.html' % int(id_))

  with open(html, 'w') as f:
    print('<a name="%(anchor)s"></a>' % record, file=f)
    print('<h2>%(title)s</h2>' % record, file=f)
    print('<p>%(comment)s</p>' % record, file=f)

    print('<div class="wc">', file=f)

    # TODO:
    # - Could make a table out of this
    # - Link path to source code

    print('<pre>', file=f)
    for count, rel_path in rows:
      count_str = '{:,}'.format(count)
      print('%6s %s' % (count_str, rel_path), file=f)
    print('</pre>', file=f)
    print('</div>', file=f)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
