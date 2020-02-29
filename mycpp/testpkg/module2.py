"""
module2.py
"""
from mylib import log

CONST2 = 'CONST module2'

def func2():
  # type: () -> None
  log('func2')

  from testpkg import module1
  log(module1.CONST1)
