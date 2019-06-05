#!/usr/bin/env python2
"""
make_zip.py

Takes a list of manifests and merges them into a zip file.
"""

import sys
import zipfile


def main(argv):
  # Write input files to a .zip
  out_path = argv[1]

  # NOTE: Startup is ~3 ms faster WITHOUT compression.  38 ms. vs 41. ms.
  #mode = zipfile.ZIP_DEFLATED

  # Increase size of bytecode, slightly faster compression, don't need zlib.
  mode = zipfile.ZIP_STORED

  z = zipfile.ZipFile(out_path, 'w', mode)

  seen = {}
  for line in sys.stdin:
    line = line.strip()
    if not line:  # Some files are hand-edited.  Allow empty lines.
      continue
    try:
      full_path, rel_path = line.split(None, 1)
    except ValueError:
      raise RuntimeError('Invalid line %r' % line)

    if rel_path in seen:
      expected = seen[rel_path]
      if expected != full_path:
        print >>sys.stderr, 'WARNING: expected %r, got %r' % (expected,
            full_path)
      continue

    #print >>sys.stderr, '%s -> %s' % (full_path, rel_path)
    z.write(full_path, rel_path)
    seen[rel_path] = full_path

  # TODO: Make summary


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'make_zip:', e.args[0]
    sys.exit(1)
