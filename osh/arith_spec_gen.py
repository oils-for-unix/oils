#!/usr/bin/env python2
"""
arith_spec_gen.py
"""
from __future__ import print_function

import sys

from osh.arith_spec import _SPEC
from core.util import log


def main(argv):
  spec = _SPEC
  log('%s', spec)

  for k, v in spec.nud_lookup.iteritems():
    log('%s %s', k, v)

  log('')
  log('')

  # TODO: namespace are arith_parse or tdop
  for k, v in spec.led_lookup.iteritems():
    log('%s %s', k, v)


  print("""
#include "osh_arith_spec.h"

// main program has no headers, so here are prototypes
namespace tdop {
  LeftFunc LeftError;
  NullFunc NullError;
}

namespace arith_spec {

tdop::LeftInfo kLeftLookup[] = {
  { tdop::LeftError, 0, 0 },
};

tdop::NullInfo kNullLookup[] = {
  { tdop::NullError, 0 },
};

};

""")


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
