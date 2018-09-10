# operation flags
OP_ASSIGN = 'OP_ASSIGN'
OP_DELETE = 'OP_DELETE'
OP_APPLY = 'OP_APPLY'

SC_LOCAL = 1
SC_GLOBAL_IMPLICIT = 2
SC_GLOBAL_EXPLICIT = 3
SC_FREE = 4
SC_CELL = 5
SC_UNKNOWN = 6

# NOTE: These really should be an ASDL enum types so we get proper names.
# Although we will also need reflection to iterate over them.
VALUE_TO_NAME = {}

def _const(name, val):
  VALUE_TO_NAME[val] = name
  globals()[name] = val
  

_const('CO_OPTIMIZED', 0x0001)
_const('CO_NEWLOCALS', 0x0002)
_const('CO_VARARGS', 0x0004)
_const('CO_VARKEYWORDS', 0x0008)
_const('CO_NESTED', 0x0010)
_const('CO_GENERATOR', 0x0020)
_const('CO_FUTURE_DIVISION', 0x2000)
_const('CO_FUTURE_ABSIMPORT', 0x4000)
_const('CO_FUTURE_WITH_STATEMENT', 0x8000)
# The only FUTURE that's relevant to us.  Everything else is the default.
_const('CO_FUTURE_PRINT_FUNCTION', 0x10000)
