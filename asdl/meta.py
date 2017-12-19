#!/usr/bin/python
"""
meta.py

Meta-Object model for ASDL.  This is available at runtime.

asdl_.py could be renamed asdl_parse.py.  It has a parser and an AST.
or parse.py

And then we need a compile_.py that resolves the types and creates a
meta-object model.

repr() of these types should correspond to Python code.  So we can print it!

TODO: Look at ASDL in ASDL from the original paper.

Serialization algorithm:
  - They all start out empty, token = ProductType(), word = SumType(),
    word.Compound = ConsType(), etc.

  - And then you iterate over fields and do


osh_asdl.py

from asdl import meta


meta_word = meta.SumType()
meta_word.CompoundWord = meta.ConsType()

meta_word.CompoundWord.fields['a'] = meta_word_part ?

class word_e(object):
  TokenWord = 1
  CompoundWord = 2
  BracedWordTree = 3
  StringWord = 4

class word(asdl_base.CompoundObj):
  ASDL_TYPE = meta_word  # instance of meta.SumType

class CompoundWord(word):
  ASDL_TYPE = meta_word.CompoundWord


So for each ASDL type, we have two Python classes
1. INSTANCE: One used to instantiate it
2. TYPE: A meta_ instance, instance of meta.Type(), that is used for
   reflection.  It is the ASDL_TYPE class attribute of the first type.


asdl_base.Instance()  # base class for all instances
asdl_meta.Type()  # base class for all types


w.ASDL_META ?  That might be a better name.

NOTE: How would you represent this in C?  By a big pointer graph?  With oheap?
Yes oheap would be nice for this!
Could we generate C code?
It would be very compact.


So then the first half of osh_asdl.py is the META_word and META_word_part, etc.

And META_INT = meta.IntType()

And then the second half is all the instances

word, word_part_e, etc.

So I need to generate them dynamically first, and then do pretty printing.

"""

class Obj(object):
  """Base class for all ASDL instances (not types)."""
  # instead of DESCRIPTOR
  #
  ASDL_TYPE = None   # instance of meta.Type


UNDEFINED, BOOL, INT, STR, SUM, PRODUCT, CONS = range(7)


class Type(object):
  tag = UNDEFINED  # invalid value

  def __repr__(self):
    raise NotImplementedError


class BoolType(Type):
  tag = BOOL

  def __repr__(self):
    return 'BoolType()'


class IntType(Type):
  tag = INT

  def __repr__(self):
    return 'IntType()'


class StrType(Type):
  tag = STR

  def __repr__(self):
    return 'StrType()'


class CompoundType(Type):
  tag = UNDEFINED  # abstract type

  def __init__(self):
    # name -> meta.Type
    #
    # The compilation process resolves names and fills this out.
    self.fields = {}

  def GetFieldType(self, name):
    # get field type
    pass

  def GetFieldTypes(self):
    # Iterate over (name, meta.Type() instances?)
    pass


class ProductType(CompoundType):
  tag = PRODUCT

  def __repr__(self):
    # It should
    # How to refer to the fields?
    # I guess you can have

    # token = ProductType()
    #
    # word_part = SumType()
    #
    # word.Compound = ConsType()
    #
    # word.Compound.fields['parts'] = word_part

    # word.Compound.fields['parts'] = word_part
    #
    #

    # word.String = ConsType()
    # word.String.fields['id'] = Id  # Oh this is the generated type
    # word.String.fields['s'] = STR_TYPE   # singleton

    return 'ProductType(TODO)'


# Usage:
#
# w = word.Compound(...)
# tag = w.ASDL_TYPE.GetTag()

# Not sure if I need this?
# tag = w.ASDL_TYPE.GetFieldType('name')
#
# I guess this is used for generic pretty printing?
# meta_tag = w.ASDL_TYPE.tag
#
# or should I use __type and __tag ?
# or TYPE and TAG
# ASDL_TYPE and ASDL_TAG?  I think that makes it more meta
# asdl_type and asdl_tag


class ConsType(CompoundType):
  tag = CONS

  def GetTag(self):
    # e.g. word.Compound or word.Token
    pass

  def __repr__(self):
    return 'ConsType(TODO)'



class SumType():
  tag = SUM

  # TODO: Does this need to know about its children types for pretty printing?
  # For type checking?

  def __repr__(self):
    return 'SumType(TODO)'



