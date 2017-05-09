#!/usr/bin/python -S
"""
make_zip.py

Takes a list of manifests and merges them into a zip file.
"""

import sys
import zipfile


def main(argv):
  # Write input files to a .zip
  out_path = argv[1]

  #mode = zipfile.ZIP_DEFLATED
  # Increase size of bytecode, but don't need zlib.  And maybe faster startup.
  mode = zipfile.ZIP_STORED

  z = zipfile.ZipFile(out_path, 'w', mode)

  seen = {}
  for manifest in argv[2:]:
    with open(manifest) as f:
      for line in f:
        line = line.strip()
        try:
          full_path, rel_path = line.split(None, 1)
        except ValueError:
          raise RuntimeError('Invalid line %r' % line)

        if rel_path in seen:
          expected = seen[rel_path]
          if expected != full_path:
            print >>sys.sterr, 'WARNING: expected %r, got %r' % (expected,
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
