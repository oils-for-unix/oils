#!/usr/bin/env python2
"""
collections.py

To avoid other dependencies.  Copied OrderedDict from collections.py, and
MutableMapping from _abcoll.
"""

from typing import Any


class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as regular dictionaries.

    # The internal self.__map dict maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(*args, **kwds):
        # type: (Any, Any) -> None
        '''Initialize an ordered dictionary.  The signature is the same as
        regular dictionaries, but keyword arguments are not recommended because
        their insertion order is arbitrary.

        '''

        if not args:
            raise TypeError("descriptor '__init__' of 'OrderedDict' object "
                            "needs an argument")
        self = args[0]
        args = args[1:]
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}

        # Oil patch
        #self.__update(*args, **kwds)
        if args:
          raise AssertionError(args)
        if kwds:
          raise AssertionError(kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link at the end of the linked list,
        # and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        return dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which gets
        # removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, _ = self.__map.pop(key)
        link_prev[1] = link_next                        # update link_prev[NEXT]
        link_next[0] = link_prev                        # update link_next[PREV]

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        # Traverse the linked list in order.
        root = self.__root
        curr = root[1]                                  # start at the first node
        while curr is not root:
            yield curr[2]                               # yield the curr[KEY]
            curr = curr[1]                              # move to next node

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        # Traverse the linked list in reverse order.
        root = self.__root
        curr = root[0]                                  # start at the last node
        while curr is not root:
            yield curr[2]                               # yield the curr[KEY]
            curr = curr[0]                              # move to previous node

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        root = self.__root
        root[:] = [root, root, None]
        self.__map.clear()
        dict.clear(self)

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        # PATCH: not used in Oil
        raise AssertionError()

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        # PATCH: not used in Oil
        raise AssertionError()

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) pairs in od'
        for k in self:
            yield (k, self[k])

    # Oils patch: commented out
    if 0:
      update = MutableMapping.update

      __update = update # let subclasses override update without breaking __init__

    # Oils patch:
    def update(self, other):
        for k, v in other.iteritems():
            self[k] = v

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding
        value.  If key is not found, d is returned if given, otherwise KeyError
        is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        # PATCH: not used in Oil
        raise AssertionError()

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        # PATCH: not used in Oil
        raise AssertionError()

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        #call_key = id(self), _get_ident()

        # Oil patch: we don't have threads
        call_key = id(self)

        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            # Oil patch: use <> as a subtle indicator of OrderedDict
            parts = ['<']
            for i, key in enumerate(self):
              if i != 0:
                parts.append(', ')
              parts.append('%r: ' % key)
              parts.append('%r' % self[key])
            parts.append('>')
            return ''.join(parts)

        finally:
            del _repr_running[call_key]

    def copy(self):
        'od.copy() -> a shallow copy of od'
        # PATCH: not used in Oil
        raise AssertionError()

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S.
        If not specified, the value defaults to None.

        '''
        # PATCH: not used in Oil
        raise AssertionError()

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        # removed _imap code
        raise AssertionError('not supported')

    def __ne__(self, other):
        'od.__ne__(y) <==> od!=y'
        return not self == other
