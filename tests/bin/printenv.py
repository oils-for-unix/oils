#!/usr/bin/env python3

import os
import sys

for name in sys.argv[1:]:
  print(os.environ.get(name))
