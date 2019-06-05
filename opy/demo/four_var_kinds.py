#!/usr/bin/env python2
"""
four_var_kinds.py

From PyCodeObject in Include/code.h:

    PyObject *co_names;		/* list of strings (names used) */
    PyObject *co_varnames;	/* tuple of strings (local variable names) */
    PyObject *co_freevars;	/* tuple of strings (free variable names) */
    PyObject *co_cellvars;      /* tuple of strings (cell variable names) */

    PyObject *co_consts;	/* list (constants used) */

I don't get what these are.
"""
# names
# varnames

def f(x):
  y = x
  return x

class C(object):
  def __init__(self):
    self.x = 1
    y = 2

# In Add bytecode:
# co_freevars:        ('left',)
# It makes sense because it's "free" -- not in the frame.

# In Adder bytecode:
# co_cellvars:        ('left',)


# I generally use classes for this, but I do use it for generator expressions.

# However the usage is quite low.  If it's down at the CPython levels, then we
# might be able to get rid of it.
# In the case of generator expressions, we could just use dynamic scope?  Not
# lexical scope?  They are equivalent in that case.

# Hm in CPython there are only 2 of my own usages!
"""
> cpy$names %>% filter(kind == 'free')
                                                            path   code_name
1                      /home/andy/git/oilshell/oil/core/args.pyc  ParseLikeEcho
2                   /home/andy/git/oilshell/oil/core/builtin.pyc _PrintDirStack

The first is all()
# See ParseLikeEcho in core/args.py:
# if not all(c in self.arity0 for c in arg[1:]):

The second is ' '.join()
"""
# TODO: I want real closures to run JS on OVM (ES3 probably).  So maybe omit
# cell and free vars?  There # are many ways to compile closures.
#
# Experiment: move everything to 'names' instead of 'varnames'?  What breaks?
# Run unit tests.

"""
> Names(cpy$names)
# A tibble: 4 x 2
  kind      n
  <chr> <int>
1 name  14342
2 var    5435
3 free     16
4 cell     14

> Names(opy$names)                                                                                                                               
# A tibble: 4 x 2
  kind      n
  <chr> <int>
1 name  18926
2 var   16581
3 free     52
4 cell     49
"""
     
def Adder(left):
  def Add(right):
    return left + right
  return Add

a = Adder(3)
print(a(5))





