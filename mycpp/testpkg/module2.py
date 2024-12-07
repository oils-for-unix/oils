from __future__ import print_function
"""
module2.py
"""
import mylib
from mylib import log

CONST2 = 'CONST module2'

def func2():
  # type: () -> None
  log('func2')

  from testpkg import module1
  mylib.print_stderr(module1.CONST1)
