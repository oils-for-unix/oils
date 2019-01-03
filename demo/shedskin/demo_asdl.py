import const  # For const.NO_INTEGER
import runtime
#from pylib import unpickle

#from core import util

#f = util.GetResourceLoader().open('_devbuild/demo_asdl.pickle')
#TYPE_LOOKUP = unpickle.load_v2_subset(f)
#f.close()
#TYPE_LOOKUP = {}

class op_id_e(runtime.SimpleObj):
  #ASDL_TYPE = TYPE_LOOKUP['op_id']
  pass

op_id_e.Plus = op_id_e(1, 'Plus')
op_id_e.Minus = op_id_e(2, 'Minus')
op_id_e.Star = op_id_e(3, 'Star')

class cflow_e(object):
  Break = 1
  Continue = 2
  Return = 3

class cflow(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['cflow']
  pass

class cflow__Break(cflow):
  #ASDL_TYPE = TYPE_LOOKUP['cflow__Break']
  tag = 1

class cflow__Continue(cflow):
  #ASDL_TYPE = TYPE_LOOKUP['cflow__Continue']
  tag = 2

class cflow__Return(cflow):
  tag = 3
  #ASDL_TYPE = TYPE_LOOKUP['cflow__Return']
  __slots__ = ('status', 'spids')

  def __init__(self, status=None, spids=None):
    self.status = status
    self.spids = spids or []

cflow.Break = cflow__Break
cflow.Continue = cflow__Continue
cflow.Return = cflow__Return

class source_location(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['source_location']
  __slots__ = ('path', 'line', 'col', 'length', 'spids')

  def __init__(self, path=None, line=None, col=None, length=None, spids=None):
    self.path = path
    self.line = line
    self.col = col
    self.length = length
    self.spids = spids or []

class token(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['token']
  __slots__ = ('id', 'value', 'span_id', 'spids')

  def __init__(self, id=None, value=None, span_id=None, spids=None):
    self.id = id
    self.value = value
    self.span_id = span_id or const.NO_INTEGER
    self.spids = spids or []

class assign(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['assign']
  __slots__ = ('name', 'flags', 'spids')

  def __init__(self, name=None, flags=None, spids=None):
    self.name = name
    self.flags = flags or []
    self.spids = spids or []

class arith_expr_e(object):
  Const = 1
  ArithVar = 2
  ArithUnary = 3
  ArithBinary = 4
  FuncCall = 5
  ForwardRef = 6
  Index = 7
  Slice = 8

class arith_expr(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr']
  pass

class arith_expr__Const(arith_expr):
  tag = 1
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__Const']
  __slots__ = ('i', 'spids')

  def __init__(self, i=None, spids=None):
    self.i = i
    self.spids = spids or []

class arith_expr__ArithVar(arith_expr):
  tag = 2
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__ArithVar']
  __slots__ = ('name', 'spids')

  def __init__(self, name=None, spids=None):
    self.name = name
    self.spids = spids or []

class arith_expr__ArithUnary(arith_expr):
  tag = 3
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__ArithUnary']
  __slots__ = ('op_id', 'a', 'spids')

  def __init__(self, op_id=None, a=None, spids=None):
    self.op_id = op_id
    self.a = a
    self.spids = spids or []

class arith_expr__ArithBinary(arith_expr):
  tag = 4
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__ArithBinary']
  __slots__ = ('op_id', 'left', 'right', 'spids')

  def __init__(self, op_id=None, left=None, right=None, spids=None):
    self.op_id = op_id
    self.left = left
    self.right = right
    self.spids = spids or []

class arith_expr__FuncCall(arith_expr):
  tag = 5
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__FuncCall']
  __slots__ = ('name', 'args', 'spids')

  def __init__(self, name=None, args=None, spids=None):
    self.name = name
    self.args = args or []
    self.spids = spids or []

class arith_expr__ForwardRef(arith_expr):
  tag = 6
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__ForwardRef']
  __slots__ = ('b', 'spids')

  def __init__(self, b=None, spids=None):
    self.b = b
    self.spids = spids or []

class arith_expr__Index(arith_expr):
  tag = 7
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__Index']
  __slots__ = ('a', 'index', 'spids')

  def __init__(self, a=None, index=None, spids=None):
    self.a = a
    self.index = index
    self.spids = spids or []

class arith_expr__Slice(arith_expr):
  tag = 8
  #ASDL_TYPE = TYPE_LOOKUP['arith_expr__Slice']
  __slots__ = ('a', 'begin', 'end', 'stride', 'spids')

  def __init__(self, a=None, begin=None, end=None, stride=None, spids=None):
    self.a = a
    self.begin = begin or None
    self.end = end or None
    self.stride = stride or None
    self.spids = spids or []

arith_expr.Const = arith_expr__Const
arith_expr.ArithVar = arith_expr__ArithVar
arith_expr.ArithUnary = arith_expr__ArithUnary
arith_expr.ArithBinary = arith_expr__ArithBinary
arith_expr.FuncCall = arith_expr__FuncCall
arith_expr.ForwardRef = arith_expr__ForwardRef
arith_expr.Index = arith_expr__Index
arith_expr.Slice = arith_expr__Slice

class word(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['word']
  __slots__ = ('value', 'spids')

  def __init__(self, value=None, spids=None):
    self.value = value
    self.spids = spids or []

class bool_expr_e(object):
  BoolBinary = 1
  BoolUnary = 2
  LogicalNot = 3
  LogicalAnd = 4
  LogicalOr = 5

class bool_expr(runtime.CompoundObj):
  #ASDL_TYPE = TYPE_LOOKUP['bool_expr']
  pass

class bool_expr__BoolBinary(bool_expr):
  tag = 1
  #ASDL_TYPE = TYPE_LOOKUP['bool_expr__BoolBinary']
  __slots__ = ('left', 'right', 'spids')

  def __init__(self, left=None, right=None, spids=None):
    self.left = left
    self.right = right
    self.spids = spids or []

class bool_expr__BoolUnary(bool_expr):
  tag = 2
  #ASDL_TYPE = TYPE_LOOKUP['bool_expr__BoolUnary']
  __slots__ = ('child', 'spids')

  def __init__(self, child=None, spids=None):
    self.child = child
    self.spids = spids or []

class bool_expr__LogicalNot(bool_expr):
  tag = 3
  #ASDL_TYPE = TYPE_LOOKUP['bool_expr__LogicalNot']
  __slots__ = ('b', 'spids')

  def __init__(self, b=None, spids=None):
    self.b = b
    self.spids = spids or []

class bool_expr__LogicalAnd(bool_expr):
  tag = 4
  #ASDL_TYPE = TYPE_LOOKUP['bool_expr__LogicalAnd']
  __slots__ = ('left', 'right', 'spids')

  def __init__(self, left=None, right=None, spids=None):
    self.left = left
    self.right = right
    self.spids = spids or []

class bool_expr__LogicalOr(bool_expr):
  tag = 5
  #ASDL_TYPE = TYPE_LOOKUP['bool_expr__LogicalOr']
  __slots__ = ('left', 'right', 'spids')

  def __init__(self, left=None, right=None, spids=None):
    self.left = left
    self.right = right
    self.spids = spids or []

bool_expr.BoolBinary = bool_expr__BoolBinary
bool_expr.BoolUnary = bool_expr__BoolUnary
bool_expr.LogicalNot = bool_expr__LogicalNot
bool_expr.LogicalAnd = bool_expr__LogicalAnd
bool_expr.LogicalOr = bool_expr__LogicalOr

