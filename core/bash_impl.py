"""bash_impl.py - implements operations on Bash data structures"""

from _devbuild.gen.runtime_asdl import error_code_e, error_code_t
from _devbuild.gen.value_asdl import value

from data_lang import j8_lite
from mycpp import mops
from mycpp import mylib

from typing import Dict, List, Optional, Tuple


def BigInt_Greater(a, b):
    # type: (mops.BigInt, mops.BigInt) -> bool

    return mops.Greater(a, b)


def BigInt_Less(a, b):
    # type: (mops.BigInt, mops.BigInt) -> bool

    return mops.Greater(b, a)


#------------------------------------------------------------------------------
# All BashArray operations depending on the internal
# representation of SparseArray come here.


def BashArray_Count(array_val):
    # type: (value.BashArray) -> int

    # There can be empty placeholder values in the array.
    length = 0
    for s in array_val.strs:
        if s is not None:
            length += 1
    return length


def BashArray_Length(array_val):
    # type: (value.BashArray) -> int

    return len(array_val.strs)


def BashArray_GetValues(array_val):
    # type: (value.BashArray) -> List[str]

    return array_val.strs


def BashArray_AppendValues(array_val, strs):
    # type: (value.BashArray, List[str]) -> None

    array_val.strs.extend(strs)


def BashArray_HasElement(val, index):
    # type: (value.BashArray, int) -> Tuple[bool, error_code_t]

    n = len(val.strs)
    if index < 0:
        index += n
        if index < 0:
            return False, error_code_e.IndexOutOfRange

    if index < n:
        return val.strs[index] is not None, error_code_e.OK

    # out of range
    return False, error_code_e.OK


def BashArray_GetElement(array_val, index):
    # type: (value.BashArray, int) -> Tuple[Optional[str], error_code_t]
    """This function returns a tuple of a string value and an
    error_code.  If the element is found, the value is returned as the
    first element of the tuple.  Otherwise, the first element of the
    tuple is None.

    """

    strs = array_val.strs
    n = len(strs)
    if index < 0:
        index += n
        if index < 0:
            return None, error_code_e.IndexOutOfRange

    if index < n:
        # TODO: strs->index() has a redundant check for (i < 0)
        s = strs[index]
        # note: s could be None because representation is sparse
    else:
        s = None
    return s, error_code_e.OK


def BashArray_SetElement(array_val, index, s):
    # type: (value.BashArray, int, str) -> error_code_t

    strs = array_val.strs

    n = len(strs)
    if index < 0:  # a[-1]++ computes this twice; could we avoid it?
        index += n
        if index < 0:
            return error_code_e.IndexOutOfRange

    if index < n:
        strs[index] = s
    else:
        # Fill it in with None.  It could look like this:
        # ['1', 2, 3, None, None, '4', None]
        # Then ${#a[@]} counts the entries that are not None.
        n = index - len(strs) + 1
        for i in xrange(n):
            strs.append(None)
        strs[index] = s

    return error_code_e.OK


def BashArray_UnsetElement(array_val, index):
    # type: (value.BashArray, int) -> error_code_t
    strs = array_val.strs

    n = len(strs)
    last_index = n - 1
    if index < 0:
        index += n
        if index < 0:
            return error_code_e.IndexOutOfRange

    if index == last_index:
        # Special case: The array SHORTENS if you unset from the end.  You can
        # tell with a+=(3 4)
        strs.pop()
        while len(strs) > 0 and strs[-1] is None:
            strs.pop()
    elif index < last_index:
        strs[index] = None
    else:
        # If it's not found, it's not an error.  In other words, 'unset'
        # ensures that a value doesn't exist, regardless of whether it existed.
        # It's idempotent.  (Ousterhout specifically argues that the strict
        # behavior was a mistake for Tcl!)
        pass

    return error_code_e.OK


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
                        " ", name, "[",
                        str(i), "]=",
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
                            "[",
                            str(i), "]=",
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


def BashAssoc_Count(assoc_val):
    # type: (value.BashAssoc) -> int
    return len(assoc_val.d)


def BashAssoc_GetValues(assoc_val):
    # type: (value.BashAssoc) -> Dict[str, str]

    return assoc_val.d


def BashAssoc_AppendValues(assoc_val, d):
    # type: (value.BashAssoc, Dict[str, str]) -> None

    for key in d:
        assoc_val.d[key] = d[key]


def BashAssoc_HasElement(assoc_val, s):
    # type: (value.BashAssoc, str) -> bool

    return s in assoc_val.d


def BashAssoc_GetElement(assoc_val, s):
    # type: (value.BashAssoc, str) -> Optional[str]

    return assoc_val.d.get(s)


def BashAssoc_SetElement(assoc_val, key, s):
    # type: (value.BashAssoc, str, str) -> None

    assoc_val.d[key] = s


def BashAssoc_UnsetElement(assoc_val, key):
    # type: (value.BashAssoc, str) -> None

    mylib.dict_erase(assoc_val.d, key)


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


def SparseArray_Count(sparse_val):
    # type: (value.SparseArray) -> int
    return len(sparse_val.d)


def SparseArray_Length(sparse_val):
    # type: (value.SparseArray) -> mops.BigInt

    return mops.Add(sparse_val.max_index, mops.ONE)


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


def _SparseArray_CanonicalizeIndex(sparse_val, index):
    # type: (value.SparseArray, mops.BigInt) -> Tuple[mops.BigInt, error_code_t]
    """This function returns (None, error_code_e.IndexOutOfRange) when
    the specified index is out of range.  For example, it includes the
    case where the index is negative and its absolute value is larger
    than max_index + 1.

    """

    if BigInt_Less(index, mops.ZERO):
        index = mops.Add(index, mops.Add(sparse_val.max_index, mops.ONE))
        if BigInt_Less(index, mops.ZERO):
            return mops.MINUS_ONE, error_code_e.IndexOutOfRange
    return index, error_code_e.OK


def SparseArray_SetElement(sparse_val, index, s):
    # type: (value.SparseArray, mops.BigInt, str) -> error_code_t

    index, error_code = _SparseArray_CanonicalizeIndex(sparse_val, index)
    if error_code != error_code_e.OK:
        return error_code
    if BigInt_Greater(index, sparse_val.max_index):
        sparse_val.max_index = index
    sparse_val.d[index] = s
    return error_code_e.OK


def SparseArray_UnsetElement(sparse_val, index):
    # type: (value.SparseArray, mops.BigInt) -> error_code_t

    index, error_code = _SparseArray_CanonicalizeIndex(sparse_val, index)
    if error_code != error_code_e.OK:
        return error_code
    mylib.dict_erase(sparse_val.d, index)

    # update max_index
    if mops.Equal(index, sparse_val.max_index):
        sparse_val.max_index = mops.MINUS_ONE
        for index in sparse_val.d:
            if mops.Greater(index, sparse_val.max_index):
                sparse_val.max_index = index
    return error_code_e.OK


def SparseArray_ToStrForShellPrint(sparse_val):
    # type: (value.SparseArray) -> str

    body = []  # type: List[str]
    for index in SparseArray_GetKeys(sparse_val):
        if len(body) > 0:
            body.append(" ")
        body.extend([
            "[",
            mops.ToStr(index), "]=",
            j8_lite.MaybeShellEncode(sparse_val.d[index])
        ])
    return "(%s)" % ''.join(body)
