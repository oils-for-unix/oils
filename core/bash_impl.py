"""bash_impl.py - implements operations on Bash data structures"""

from _devbuild.gen.value_asdl import value


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
