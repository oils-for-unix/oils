#!/usr/bin/env python3

# Hm deprecation warning, may not parse Python 3.10.  That's OK for us.

import sys
from lib2to3.main import main

#print(sys.path)

# devtools/fixes/ package
sys.exit(main(".fixes"))
