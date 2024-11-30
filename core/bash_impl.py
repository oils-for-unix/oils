"""bash_impl.py - implements operations on Bash data structures"""

from _devbuild.gen.value_asdl import value

from data_lang import j8_lite
from mycpp import mops
from mycpp import mylib

from typing import List, Optional


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

def _BashArray_HasHoles(array_val):
    # type: (value.BashArray) -> bool

    # mycpp rewrite: None in array_val.strs
    for s in array_val.strs:
        if s is None:
            return True
    return False

def BashArray_ToStrForShellPrint(array_val, name):
    # type: (value.BashArray, Optional[str]) -> str

    buff = []  # type: List[str]
    first = True
    if _BashArray_HasHoles(array_val):
        if name is not None:
            # Note: Arrays with unset elements are printed in the form:
            #   declare -p arr=(); arr[3]='' arr[4]='foo' ...
            # Note: This form will be deprecated in the future when
            # InitializerList for the compound assignment a=([i]=v ...) is
            # implemented.
            buff.append("()")
            for i, element in enumerate(array_val.strs):
                if element is not None:
                    if first:
                        buff.append(";")
                        first = False
                    buff.extend([
                        " ", name, "[", str(i), "]=",
                        j8_lite.MaybeShellEncode(element)
                    ])
        else:
            buff.append("(")
            for i, element in enumerate(array_val.strs):
                if element is not None:
                    if not first:
                        buff.append(" ")
                    else:
                        first = False
                        buff.extend([
                            "[", str(i), "]=",
                            j8_lite.MaybeShellEncode(element)
                        ])
            buff.append(")")
    else:
        buff.append("(")
        for element in array_val.strs:
            if not first:
                buff.append(" ")
            else:
                first = False
            buff.append(j8_lite.MaybeShellEncode(element))
        buff.append(")")

    return ''.join(buff)

#------------------------------------------------------------------------------
# All BashAssoc operations depending on the internal
# representation of SparseArray come here.

def BashAssoc_Length(assoc_val):
    # type: (value.BashAssoc) -> int
    return len(assoc_val.d)

def BashAssoc_ToStrForShellPrint(assoc_val):
    # type: (value.BashAssoc) -> str

    buff = ["("]  # type: List[str]
    first = True
    for key in sorted(assoc_val.d):
        if not first:
            buff.append(" ")
        else:
            first = False

        key_quoted = j8_lite.ShellEncode(key)
        value_quoted = j8_lite.MaybeShellEncode(assoc_val.d[key])

        buff.extend(["[", key_quoted, "]=", value_quoted])

    buff.append(")")
    return ''.join(buff)

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
