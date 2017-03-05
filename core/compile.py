"""
compile.py: osh.asdl -> ovm.asdl

Things the compiler should do:

- AndOr is parsed with right recursion?  So expand that into a list?  Or
  execute with left recursion?

- assignments need to be desugared into a lot of differrent things.
  - for now everything is Dynamic?  ONLY hash tables.
  - yeah osh ONLY has hash tables, even for locals, like bash.
  - oil will have a proper compiler I think.  It can do stack analysis.
    Because it requires "global" and so forth.

- while/until compiled to same thing.
  - maybe

- DoGroup/BraceGroup compiled to same thing
  - CommandList might be removed later

- Sentence is compiled to Fork(), or nothing for ;

- else_action in If should be compiled uniformly
- might want to also compile case/if to same thing

- [[ ]] and arith languages will have grouping parens for printing.  Eliminate
  those and use tree structure.

- constant folding:
  - especially of literal strings, concatenating escapes, etc.

- maybe compile differently based on module-level :option

- not sure if redirects need to be separate into primitive push/pop




"""

import sys


def main(argv):
  print 'Hello from compile.py'


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
