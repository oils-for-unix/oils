#!/usr/bin/env python2
"""
tea_eval.py

Extracted from ysh/cmd_eval.py.  THIS DOES DOESN'T RUN YET.

TODO: Test it.

"""
from __future__ import print_function

import sys


class Func(object):

  def __init__(self, node, pos_defaults, named_defaults, cmd_ev):
    # type: (command.TeaFunc, List[Any], Dict[str, Any], CommandEvaluator) -> None
    self.node = node
    self.pos_defaults = pos_defaults
    self.named_defaults = named_defaults
    self.cmd_ev = cmd_ev

  def __call__(self, *args, **kwargs):
    # type: (*Any, **Any) -> Any
    raise NotImplementedError()
    # Moved to tea
    #return self.cmd_ev.RunOilFunc(self, args, kwargs)


class TeaEvaluator(object):

  def RunOilFunc(self, func, args, kwargs):
    # type: (Func, Tuple[Any, ...], Dict[str, Any]) -> Any
    """Run an Oil function.

    var x = abs(y)   do f(x)   @split(mystr)   @join(myarray)
    """
    # TODO:
    # - Return value register should be separate?
    #   - But how does 'return 345' work?  Is that the return builtin
    #     raising an exception?
    #     Or is it setting the register?
    #   - I think the exception can have any type, but when you catch it
    #     you determine whether it's LastStatus() or it's something else.
    #   - Something declared with 'func' CANNOT have both?
    #
    # - Type checking
    #   - If the arguments are all strings, make them @ARGV?
    #     That isn't happening right now.

    #log('RunOilFunc kwargs %s', kwargs)
    #log('RunOilFunc named_defaults %s', func.named_defaults)

    node = func.node
    self.mem.PushTemp()

    # Bind positional arguments
    n_args = len(args)
    n_params = len(node.pos_params)
    for i, param in enumerate(node.pos_params):
      if i < n_args:
        py_val = args[i]
        val = _PyObjectToVal(py_val)
      else:
        val = func.pos_defaults[i]
        if val is None:
          # Python raises TypeError.  Should we do something else?
          raise TypeError('No value provided for param %r', param.name)
      self.mem.SetValue(location.LName(param.name.val), val, scope_e.LocalOnly)

    if node.pos_splat:
      splat_name = node.pos_splat.val

      # NOTE: This is a heterogeneous TUPLE, not list.
      leftover = value.Obj(args[n_params:])
      self.mem.SetValue(location.LName(splat_name), leftover, scope_e.LocalOnly)
    else:
      if n_args > n_params:
        raise TypeError(
            "func %r expected %d arguments, but got %d" %
            (node.name.val, n_params, n_args))

    # Bind named arguments
    for i, param in enumerate(node.named_params):
      name = param.name
      if name.val in kwargs:
        py_val = kwargs.pop(name.val)  # REMOVE it
        val = _PyObjectToVal(py_val)
      else:
        if name.val in func.named_defaults:
          val = func.named_defaults[name.val]
        else:
          raise TypeError(
              "Named argument %r wasn't passed, and it doesn't have a default "
              "value" % name.val)

      self.mem.SetValue(location.LName(name.val), val, scope_e.LocalOnly)

    if node.named_splat:
      splat_name = node.named_splat.val
      # Note: this dict is not an BashAssoc
      leftover = value.Obj(kwargs)
      self.mem.SetValue(location.LName(splat_name), leftover, scope_e.LocalOnly)
    else:
      if kwargs:
        raise TypeError(
            'func %r got unexpected named arguments: %s' %
            (node.name.val, ', '.join(kwargs.keys())))

    return_val = None  # type: int
    try:
      self._Execute(node.body)
    except _ControlFlow as e:
      if e.IsReturn():
        # TODO: Rename this
        return_val = e.StatusCode()
    finally:
      self.mem.PopTemp()
    return return_val

  def RunLambda(self, lambda_node, args, kwargs):
    # type: (expr.Lambda, Tuple[Any, ...], Dict[str, Any]) -> Any
    """ Run a lambda like |x| x+1 """

    self.mem.PushTemp()
    # Bind params.  TODO: Reject kwargs, etc.
    for i, param in enumerate(lambda_node.params):
      val = value.Obj(args[i])
      self.mem.SetValue(location.LName(param.name.val), val, scope_e.LocalOnly)

    return_val = None
    try:
      return_val = self.expr_ev.EvalExpr(lambda_node.body)
    finally:
      self.mem.PopTemp()
    return return_val
