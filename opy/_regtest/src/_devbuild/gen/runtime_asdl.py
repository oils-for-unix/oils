from asdl import const  # For const.NO_INTEGER
from asdl import py_meta
from osh.meta import RUNTIME_TYPE_LOOKUP as TYPE_LOOKUP

class part_value_e(object):
  StringPartValue = 1
  ArrayPartValue = 2

class part_value(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('part_value')

class StringPartValue(part_value):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('StringPartValue')
  __slots__ = ('s', 'do_split_glob', 'spids')

  def __init__(self, s=None, do_split_glob=None, spids=None):
    self.s = s
    self.do_split_glob = do_split_glob
    self.spids = spids or []

class ArrayPartValue(part_value):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ArrayPartValue')
  __slots__ = ('strs', 'spids')

  def __init__(self, strs=None, spids=None):
    self.strs = strs or []
    self.spids = spids or []

class value_e(object):
  Undef = 1
  Str = 2
  StrArray = 3

class value(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('value')

class Undef(value):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Undef')
  tag = 1

class Str(value):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('Str')
  __slots__ = ('s', 'spids')

  def __init__(self, s=None, spids=None):
    self.s = s
    self.spids = spids or []

class StrArray(value):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('StrArray')
  __slots__ = ('strs', 'spids')

  def __init__(self, strs=None, spids=None):
    self.strs = strs or []
    self.spids = spids or []

class cell(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('cell')
  __slots__ = ('val', 'exported', 'readonly', 'spids')

  def __init__(self, val=None, exported=None, readonly=None, spids=None):
    self.val = val
    self.exported = exported
    self.readonly = readonly
    self.spids = spids or []

class var_flags_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('var_flags')

var_flags_e.Exported = var_flags_e(1, 'Exported')
var_flags_e.ReadOnly = var_flags_e(2, 'ReadOnly')

class scope_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('scope')

scope_e.TempEnv = scope_e(1, 'TempEnv')
scope_e.LocalOnly = scope_e(2, 'LocalOnly')
scope_e.GlobalOnly = scope_e(3, 'GlobalOnly')
scope_e.Dynamic = scope_e(4, 'Dynamic')

class lvalue_e(object):
  LhsName = 1
  LhsIndexedName = 2

class lvalue(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('lvalue')

class LhsName(lvalue):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LhsName')
  __slots__ = ('name', 'spids')

  def __init__(self, name=None, spids=None):
    self.name = name
    self.spids = spids or []

class LhsIndexedName(lvalue):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('LhsIndexedName')
  __slots__ = ('name', 'index', 'spids')

  def __init__(self, name=None, index=None, spids=None):
    self.name = name
    self.index = index
    self.spids = spids or []

class redirect_e(object):
  PathRedirect = 1
  DescRedirect = 2
  HereRedirect = 3

class redirect(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('redirect')

class PathRedirect(redirect):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('PathRedirect')
  __slots__ = ('op_id', 'fd', 'filename', 'spids')

  def __init__(self, op_id=None, fd=None, filename=None, spids=None):
    self.op_id = op_id
    self.fd = fd
    self.filename = filename
    self.spids = spids or []

class DescRedirect(redirect):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('DescRedirect')
  __slots__ = ('op_id', 'fd', 'target_fd', 'spids')

  def __init__(self, op_id=None, fd=None, target_fd=None, spids=None):
    self.op_id = op_id
    self.fd = fd
    self.target_fd = target_fd
    self.spids = spids or []

class HereRedirect(redirect):
  tag = 3
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('HereRedirect')
  __slots__ = ('fd', 'body', 'spids')

  def __init__(self, fd=None, body=None, spids=None):
    self.fd = fd
    self.body = body
    self.spids = spids or []

class job_status_e(object):
  ProcessStatus = 1
  PipelineStatus = 2

class job_status(py_meta.CompoundObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('job_status')

class ProcessStatus(job_status):
  tag = 1
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('ProcessStatus')
  __slots__ = ('status', 'spids')

  def __init__(self, status=None, spids=None):
    self.status = status
    self.spids = spids or []

class PipelineStatus(job_status):
  tag = 2
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('PipelineStatus')
  __slots__ = ('statuses', 'spids')

  def __init__(self, statuses=None, spids=None):
    self.statuses = statuses or []
    self.spids = spids or []

class span_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('span')

span_e.Black = span_e(1, 'Black')
span_e.Delim = span_e(2, 'Delim')
span_e.Backslash = span_e(3, 'Backslash')

class builtin_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('builtin')

builtin_e.NONE = builtin_e(1, 'NONE')
builtin_e.READ = builtin_e(2, 'READ')
builtin_e.ECHO = builtin_e(3, 'ECHO')
builtin_e.SHIFT = builtin_e(4, 'SHIFT')
builtin_e.CD = builtin_e(5, 'CD')
builtin_e.PUSHD = builtin_e(6, 'PUSHD')
builtin_e.POPD = builtin_e(7, 'POPD')
builtin_e.DIRS = builtin_e(8, 'DIRS')
builtin_e.EXPORT = builtin_e(9, 'EXPORT')
builtin_e.UNSET = builtin_e(10, 'UNSET')
builtin_e.SET = builtin_e(11, 'SET')
builtin_e.SHOPT = builtin_e(12, 'SHOPT')
builtin_e.TRAP = builtin_e(13, 'TRAP')
builtin_e.UMASK = builtin_e(14, 'UMASK')
builtin_e.SOURCE = builtin_e(15, 'SOURCE')
builtin_e.DOT = builtin_e(16, 'DOT')
builtin_e.EVAL = builtin_e(17, 'EVAL')
builtin_e.EXEC = builtin_e(18, 'EXEC')
builtin_e.WAIT = builtin_e(19, 'WAIT')
builtin_e.JOBS = builtin_e(20, 'JOBS')
builtin_e.COMPLETE = builtin_e(21, 'COMPLETE')
builtin_e.COMPGEN = builtin_e(22, 'COMPGEN')
builtin_e.DEBUG_LINE = builtin_e(23, 'DEBUG_LINE')
builtin_e.TRUE = builtin_e(24, 'TRUE')
builtin_e.FALSE = builtin_e(25, 'FALSE')
builtin_e.COLON = builtin_e(26, 'COLON')
builtin_e.TEST = builtin_e(27, 'TEST')
builtin_e.BRACKET = builtin_e(28, 'BRACKET')
builtin_e.GETOPTS = builtin_e(29, 'GETOPTS')
builtin_e.COMMAND = builtin_e(30, 'COMMAND')
builtin_e.TYPE = builtin_e(31, 'TYPE')
builtin_e.HELP = builtin_e(32, 'HELP')
builtin_e.DECLARE = builtin_e(33, 'DECLARE')
builtin_e.TYPESET = builtin_e(34, 'TYPESET')

class effect_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('effect')

effect_e.SpliceParts = effect_e(1, 'SpliceParts')
effect_e.Error = effect_e(2, 'Error')
effect_e.SpliceAndAssign = effect_e(3, 'SpliceAndAssign')
effect_e.NoOp = effect_e(4, 'NoOp')

class process_state_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('process_state')

process_state_e.Init = process_state_e(1, 'Init')
process_state_e.Done = process_state_e(2, 'Done')

class completion_state_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('completion_state')

completion_state_e.NONE = completion_state_e(1, 'NONE')
completion_state_e.FIRST = completion_state_e(2, 'FIRST')
completion_state_e.REST = completion_state_e(3, 'REST')
completion_state_e.VAR_NAME = completion_state_e(4, 'VAR_NAME')
completion_state_e.HASH_KEY = completion_state_e(5, 'HASH_KEY')
completion_state_e.REDIR_FILENAME = completion_state_e(6, 'REDIR_FILENAME')

class word_style_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('word_style')

word_style_e.Expr = word_style_e(1, 'Expr')
word_style_e.Unquoted = word_style_e(2, 'Unquoted')
word_style_e.DQ = word_style_e(3, 'DQ')
word_style_e.SQ = word_style_e(4, 'SQ')

