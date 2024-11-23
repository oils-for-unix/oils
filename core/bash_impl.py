"""bash_impl.py - implements operations on Bash data structures"""

from _devbuild.gen.value_asdl import value

from data_lang import j8_lite
from mycpp import mops
from mycpp import mylib

from typing import List


#------------------------------------------------------------------------------
# All BashArray operations depending on the internal
# representation of SparseArray come here.

def BashArray_Length(array_val):
    # type: (value.BashArray) -> int

    # There can be empty placeholder values in the array.
    length = 0
    for s in array_val.strs:
        if s is not None:
            length += 1
    return length

#------------------------------------------------------------------------------
# All BashAssoc operations depending on the internal
# representation of SparseArray come here.

def BashAssoc_Length(assoc_val):
    # type: (value.BashAssoc) -> int
    return len(assoc_val.d)

#------------------------------------------------------------------------------
# All SparseArray operations depending on the internal
# representation of SparseArray come here.

def SparseArray_Length(sparse_val):
    # type: (value.SparseArray) -> int
    return len(sparse_val.d)

def SparseArray_ToStrForShellPrint(sparse_val):
    # type: (value.SparseArray) -> str

    body = [] # type: List[str]
    keys = sparse_val.d.keys()
    mylib.BigIntSort(keys)
    for index in keys:
        if len(body) > 0:
            body.append(" ")
        body.extend([
            "[", mops.ToStr(index), "]=",
            j8_lite.MaybeShellEncode(sparse_val.d[index])
        ])
    return "(%s)" % ''.join(body)
