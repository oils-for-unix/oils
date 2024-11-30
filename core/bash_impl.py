"""bash_impl.py - implements operations on Bash data structures"""

from _devbuild.gen.value_asdl import value

from data_lang import j8_lite
from mycpp import mops
from mycpp import mylib

from typing import Dict, List, Optional


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

def BashArray_GetValues(array_val):
    # type: (value.BashArray) -> List[str]

    return array_val.strs

def BashArray_AppendValues(array_val, strs):
    # type: (value.BashArray, List[str]) -> None

    array_val.strs.extend(strs)

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

def BashAssoc_GetValues(assoc_val):
    # type: (value.BashAssoc) -> Dict[str, str]

    return assoc_val.d

def BashAssoc_AppendValues(assoc_val, d):
    # type: (value.BashAssoc, Dict[str, str]) -> None

    for key in d.keys():
        assoc_val.d[key] = d[key]

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

def SparseArray_GetKeys(sparse_val):
    # type: (value.SparseArray) -> List[mops.BigInt]

    keys = sparse_val.d.keys()
    mylib.BigIntSort(keys)
    return keys

def SparseArray_GetValues(sparse_val):
    # type: (value.SparseArray) -> List[str]
    """Get the list of values.  This function does not fill None for
    the unset elements, so the index in the returned list does not
    match the index in a sparse array.

    """

    values = []  # type: List[str]
    for index in SparseArray_GetKeys(sparse_val):
        values.append(sparse_val.d[index])
    return values

def SparseArray_AppendValues(sparse_val, strs):
    # type: (value.SparseArray, List[str]) ->  None
    for s in strs:
        sparse_val.max_index = mops.Add(sparse_val.max_index, mops.ONE)
        sparse_val.d[sparse_val.max_index] = s

def SparseArray_ToStrForShellPrint(sparse_val):
    # type: (value.SparseArray) -> str

    body = [] # type: List[str]
    for index in SparseArray_GetKeys(sparse_val):
        if len(body) > 0:
            body.append(" ")
        body.extend([
            "[", mops.ToStr(index), "]=",
            j8_lite.MaybeShellEncode(sparse_val.d[index])
        ])
    return "(%s)" % ''.join(body)
