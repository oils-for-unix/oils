# Stripped down version of typing.py!
#
# We got rid of runtime dependences on collections.py, copy.py, etc.
#
# MyPy has its own version of this, since it's written in Python 3.  We don't
# need any support at runtime.
#
# All the code retained below (~500 out of ~2000 lines) is to support:
#
# NullFunc = Callable[[int, int], int]
#
# There is some special magic to use [] aka __getitem__ with un-hashable list
# objects.  I'm not sure what that is, and it could probably be reduced
# further.


List = None
Tuple = None
Optional = None
IO = None
Dict = None
Iterator = None
Any = None
NoReturn = None


def _get_type_vars(types, tvars):
    for t in types:
        if isinstance(t, TypingMeta) or isinstance(t, _TypingBase):
            t._get_type_vars(tvars)


def _type_vars(types):
    tvars = []
    _get_type_vars(types, tvars)
    return tuple(tvars)


def _next_in_mro(cls):
    """Helper for Generic.__new__.

    Returns the class after the last occurrence of Generic or
    Generic[...] in cls.__mro__.
    """
    next_in_mro = object
    # Look for the last occurrence of Generic or Generic[...].
    for i, c in enumerate(cls.__mro__[:-1]):
        if isinstance(c, GenericMeta) and c._gorg is Generic:
            next_in_mro = cls.__mro__[i + 1]
    return next_in_mro


class TypingMeta(type):
    """Metaclass for most types defined in typing module
    (not a part of public API).

    This also defines a dummy constructor (all the work for most typing
    constructs is done in __new__) and a nicer repr().
    """

    _is_protocol = False

    def __new__(cls, name, bases, namespace):
        return super(TypingMeta, cls).__new__(cls, str(name), bases, namespace)

    @classmethod
    def assert_no_subclassing(cls, bases):
        for base in bases:
            if isinstance(base, cls):
                raise TypeError("Cannot subclass %s" %
                                (', '.join(map(_type_repr, bases)) or '()'))

    def __init__(self, *args, **kwds):
        pass

    def _eval_type(self, globalns, localns):
        """Override this in subclasses to interpret forward references.

        For example, List['C'] is internally stored as
        List[_ForwardRef('C')], which should evaluate to List[C],
        where C is an object found in globalns or localns (searching
        localns first, of course).
        """
        return self

    def _get_type_vars(self, tvars):
        pass

    def __repr__(self):
        qname = _trim_name(_qualname(self))
        return '%s.%s' % (self.__module__, qname)


class _TypingBase(object):
    """Internal indicator of special typing constructs."""
    __metaclass__ = TypingMeta
    __slots__ = ('__weakref__',)

    def __init__(self, *args, **kwds):
        pass

    def __new__(cls, *args, **kwds):
        """Constructor.

        This only exists to give a better error message in case
        someone tries to subclass a special typing object (not a good idea).
        """
        if (len(args) == 3 and
                isinstance(args[0], str) and
                isinstance(args[1], tuple)):
            # Close enough.
            raise TypeError("Cannot subclass %r" % cls)
        return super(_TypingBase, cls).__new__(cls)

    # Things that are not classes also need these.
    def _eval_type(self, globalns, localns):
        return self

    def _get_type_vars(self, tvars):
        pass

    def __repr__(self):
        cls = type(self)
        qname = _trim_name(_qualname(cls))
        return '%s.%s' % (cls.__module__, qname)

    def __call__(self, *args, **kwds):
        raise TypeError("Cannot instantiate %r" % type(self))

# Prevent checks for Generic to crash when defining Generic.
Generic = None

#class GenericMeta(TypingMeta, abc.ABCMeta):
class GenericMeta(TypingMeta):
    """Metaclass for generic types.

    This is a metaclass for typing.Generic and generic ABCs defined in
    typing module. User defined subclasses of GenericMeta can override
    __new__ and invoke super().__new__. Note that GenericMeta.__new__
    has strict rules on what is allowed in its bases argument:
    * plain Generic is disallowed in bases;
    * Generic[...] should appear in bases at most once;
    * if Generic[...] is present, then it should list all type variables
      that appear in other bases.
    In addition, type of all generic bases is erased, e.g., C[int] is
    stripped to plain C.
    """

    def __new__(cls, name, bases, namespace,
                tvars=None, args=None, origin=None, extra=None, orig_bases=None):
        """Create a new generic class. GenericMeta.__new__ accepts
        keyword arguments that are used for internal bookkeeping, therefore
        an override should pass unused keyword arguments to super().
        """
        if tvars is not None:
            # Called from __getitem__() below.
            assert origin is not None
            assert all(isinstance(t, TypeVar) for t in tvars), tvars
        else:
            # Called from class statement.
            assert tvars is None, tvars
            assert args is None, args
            assert origin is None, origin

            # Get the full set of tvars from the bases.
            tvars = _type_vars(bases)
            # Look for Generic[T1, ..., Tn].
            # If found, tvars must be a subset of it.
            # If not found, tvars is it.
            # Also check for and reject plain Generic,
            # and reject multiple Generic[...].
            gvars = None
            for base in bases:
                if base is Generic:
                    raise TypeError("Cannot inherit from plain Generic")
                if (isinstance(base, GenericMeta) and
                        base.__origin__ is Generic):
                    if gvars is not None:
                        raise TypeError(
                            "Cannot inherit from Generic[...] multiple types.")
                    gvars = base.__parameters__
            if gvars is None:
                gvars = tvars
            else:
                tvarset = set(tvars)
                gvarset = set(gvars)
                if not tvarset <= gvarset:
                    raise TypeError(
                        "Some type variables (%s) "
                        "are not listed in Generic[%s]" %
                        (", ".join(str(t) for t in tvars if t not in gvarset),
                         ", ".join(str(g) for g in gvars)))
                tvars = gvars

        initial_bases = bases
        if extra is None:
            extra = namespace.get('__extra__')
        if extra is not None and type(extra) is abc.ABCMeta and extra not in bases:
            bases = (extra,) + bases
        bases = tuple(b._gorg if isinstance(b, GenericMeta) else b for b in bases)

        # remove bare Generic from bases if there are other generic bases
        if any(isinstance(b, GenericMeta) and b is not Generic for b in bases):
            bases = tuple(b for b in bases if b is not Generic)
        namespace.update({'__origin__': origin, '__extra__': extra})
        self = super(GenericMeta, cls).__new__(cls, name, bases, namespace)
        super(GenericMeta, self).__setattr__('_gorg',
                                             self if not origin else origin._gorg)

        self.__parameters__ = tvars
        # Be prepared that GenericMeta will be subclassed by TupleMeta
        # and CallableMeta, those two allow ..., (), or [] in __args___.
        self.__args__ = tuple(Ellipsis if a is _TypingEllipsis else
                              () if a is _TypingEmpty else
                              a for a in args) if args else None
        # Speed hack (https://github.com/python/typing/issues/196).
        self.__next_in_mro__ = _next_in_mro(self)
        # Preserve base classes on subclassing (__bases__ are type erased now).
        if orig_bases is None:
            self.__orig_bases__ = initial_bases

        # This allows unparameterized generic collections to be used
        # with issubclass() and isinstance() in the same way as their
        # collections.abc counterparts (e.g., isinstance([], Iterable)).
        if (
            '__subclasshook__' not in namespace and extra or
            # allow overriding
            getattr(self.__subclasshook__, '__name__', '') == '__extrahook__'
        ):
            self.__subclasshook__ = _make_subclasshook(self)

        if origin and hasattr(origin, '__qualname__'):  # Fix for Python 3.2.
            self.__qualname__ = origin.__qualname__
        self.__tree_hash__ = (hash(self._subs_tree()) if origin else
                              super(GenericMeta, self).__hash__())
        return self

    def __init__(self, *args, **kwargs):
        super(GenericMeta, self).__init__(*args, **kwargs)
        #if isinstance(self.__extra__, abc.ABCMeta):
        if False:
            self._abc_registry = self.__extra__._abc_registry
            self._abc_cache = self.__extra__._abc_cache
        elif self.__origin__ is not None:
            self._abc_registry = self.__origin__._abc_registry
            self._abc_cache = self.__origin__._abc_cache

    # _abc_negative_cache and _abc_negative_cache_version
    # realised as descriptors, since GenClass[t1, t2, ...] always
    # share subclass info with GenClass.
    # This is an important memory optimization.
    @property
    def _abc_negative_cache(self):
        if isinstance(self.__extra__, abc.ABCMeta):
            return self.__extra__._abc_negative_cache
        return self._gorg._abc_generic_negative_cache

    @_abc_negative_cache.setter
    def _abc_negative_cache(self, value):
        if self.__origin__ is None:
            if isinstance(self.__extra__, abc.ABCMeta):
                self.__extra__._abc_negative_cache = value
            else:
                self._abc_generic_negative_cache = value

    @property
    def _abc_negative_cache_version(self):
        if isinstance(self.__extra__, abc.ABCMeta):
            return self.__extra__._abc_negative_cache_version
        return self._gorg._abc_generic_negative_cache_version

    @_abc_negative_cache_version.setter
    def _abc_negative_cache_version(self, value):
        if self.__origin__ is None:
            if isinstance(self.__extra__, abc.ABCMeta):
                self.__extra__._abc_negative_cache_version = value
            else:
                self._abc_generic_negative_cache_version = value

    def _get_type_vars(self, tvars):
        if self.__origin__ and self.__parameters__:
            _get_type_vars(self.__parameters__, tvars)

    def _eval_type(self, globalns, localns):
        ev_origin = (self.__origin__._eval_type(globalns, localns)
                     if self.__origin__ else None)
        ev_args = tuple(_eval_type(a, globalns, localns) for a
                        in self.__args__) if self.__args__ else None
        if ev_origin == self.__origin__ and ev_args == self.__args__:
            return self
        return self.__class__(self.__name__,
                              self.__bases__,
                              dict(self.__dict__),
                              tvars=_type_vars(ev_args) if ev_args else None,
                              args=ev_args,
                              origin=ev_origin,
                              extra=self.__extra__,
                              orig_bases=self.__orig_bases__)

    def __repr__(self):
        if self.__origin__ is None:
            return super(GenericMeta, self).__repr__()
        return self._tree_repr(self._subs_tree())

    def _tree_repr(self, tree):
        arg_list = []
        for arg in tree[1:]:
            if arg == ():
                arg_list.append('()')
            elif not isinstance(arg, tuple):
                arg_list.append(_type_repr(arg))
            else:
                arg_list.append(arg[0]._tree_repr(arg))
        return super(GenericMeta, self).__repr__() + '[%s]' % ', '.join(arg_list)

    def _subs_tree(self, tvars=None, args=None):
        if self.__origin__ is None:
            return self
        tree_args = _subs_tree(self, tvars, args)
        return (self._gorg,) + tuple(tree_args)

    def __eq__(self, other):
        if not isinstance(other, GenericMeta):
            return NotImplemented
        if self.__origin__ is None or other.__origin__ is None:
            return self is other
        return self.__tree_hash__ == other.__tree_hash__

    def __hash__(self):
        return self.__tree_hash__

    #@_tp_cache
    def __getitem__(self, params):
        if not isinstance(params, tuple):
            params = (params,)
        if not params and self._gorg is not Tuple:
            raise TypeError(
                "Parameter list to %s[...] cannot be empty" % _qualname(self))
        msg = "Parameters to generic types must be types."
        params = tuple(_type_check(p, msg) for p in params)
        if self is Generic:
            # Generic can only be subscripted with unique type variables.
            if not all(isinstance(p, TypeVar) for p in params):
                raise TypeError(
                    "Parameters to Generic[...] must all be type variables")
            if len(set(params)) != len(params):
                raise TypeError(
                    "Parameters to Generic[...] must all be unique")
            tvars = params
            args = params
        elif self in (Tuple, Callable):
            tvars = _type_vars(params)
            args = params
        elif self is _Protocol:
            # _Protocol is internal, don't check anything.
            tvars = params
            args = params
        elif self.__origin__ in (Generic, _Protocol):
            # Can't subscript Generic[...] or _Protocol[...].
            raise TypeError("Cannot subscript already-subscripted %s" %
                            repr(self))
        else:
            # Subscripting a regular Generic subclass.
            _check_generic(self, params)
            tvars = _type_vars(params)
            args = params

        prepend = (self,) if self.__origin__ is None else ()
        return self.__class__(self.__name__,
                              prepend + self.__bases__,
                              dict(self.__dict__),
                              tvars=tvars,
                              args=args,
                              origin=self,
                              extra=self.__extra__,
                              orig_bases=self.__orig_bases__)

    def __subclasscheck__(self, cls):
        if self.__origin__ is not None:
            # This should only be modules within the standard
            # library. singledispatch is the only exception, because
            # it's a Python 2 backport of functools.singledispatch.
            if sys._getframe(1).f_globals['__name__'] not in ['abc', 'functools',
                                                              'singledispatch']:
                raise TypeError("Parameterized generics cannot be used with class "
                                "or instance checks")
            return False
        if self is Generic:
            raise TypeError("Class %r cannot be used with class "
                            "or instance checks" % self)
        return super(GenericMeta, self).__subclasscheck__(cls)

    def __instancecheck__(self, instance):
        # Since we extend ABC.__subclasscheck__ and
        # ABC.__instancecheck__ inlines the cache checking done by the
        # latter, we must extend __instancecheck__ too. For simplicity
        # we just skip the cache check -- instance checks for generic
        # classes are supposed to be rare anyways.
        if not isinstance(instance, type):
            return issubclass(instance.__class__, self)
        return False

    def __setattr__(self, attr, value):
        # We consider all the subscripted genrics as proxies for original class
        if (
            attr.startswith('__') and attr.endswith('__') or
            attr.startswith('_abc_')
        ):
            super(GenericMeta, self).__setattr__(attr, value)
        else:
            super(GenericMeta, self._gorg).__setattr__(attr, value)


class Generic(object):
    """Abstract base class for generic types.

    A generic type is typically declared by inheriting from
    this class parameterized with one or more type variables.
    For example, a generic mapping type might be defined as::

      class Mapping(Generic[KT, VT]):
          def __getitem__(self, key: KT) -> VT:
              ...
          # Etc.

    This class can then be used as follows::

      def lookup_name(mapping: Mapping[KT, VT], key: KT, default: VT) -> VT:
          try:
              return mapping[key]
          except KeyError:
              return default
    """

    __metaclass__ = GenericMeta
    __slots__ = ()

    def __new__(cls, *args, **kwds):
        if cls._gorg is Generic:
            raise TypeError("Type Generic cannot be instantiated; "
                            "it can be used only as a base class")
        return _generic_new(cls.__next_in_mro__, cls, *args, **kwds)




class CallableMeta(GenericMeta):
    """ Metaclass for Callable."""

    def __repr__(self):
        if self.__origin__ is None:
            return super(CallableMeta, self).__repr__()
        return self._tree_repr(self._subs_tree())

    def _tree_repr(self, tree):
        if self._gorg is not Callable:
            return super(CallableMeta, self)._tree_repr(tree)
        # For actual Callable (not its subclass) we override
        # super(CallableMeta, self)._tree_repr() for nice formatting.
        arg_list = []
        for arg in tree[1:]:
            if not isinstance(arg, tuple):
                arg_list.append(_type_repr(arg))
            else:
                arg_list.append(arg[0]._tree_repr(arg))
        if arg_list[0] == '...':
            return repr(tree[0]) + '[..., %s]' % arg_list[1]
        return (repr(tree[0]) +
                '[[%s], %s]' % (', '.join(arg_list[:-1]), arg_list[-1]))

    def __getitem__(self, parameters):
        """A thin wrapper around __getitem_inner__ to provide the latter
        with hashable arguments to improve speed.
        """

        if self.__origin__ is not None or self._gorg is not Callable:
            return super(CallableMeta, self).__getitem__(parameters)
        if not isinstance(parameters, tuple) or len(parameters) != 2:
            raise TypeError("Callable must be used as "
                            "Callable[[arg, ...], result].")
        args, result = parameters
        if args is Ellipsis:
            parameters = (Ellipsis, result)
        else:
            if not isinstance(args, list):
                raise TypeError("Callable[args, result]: args must be a list."
                                " Got %.100r." % (args,))
            parameters = (tuple(args), result)
        return self.__getitem_inner__(parameters)

    #@_tp_cache
    def __getitem_inner__(self, parameters):
        args, result = parameters
        msg = "Callable[args, result]: result must be a type."
        result = _type_check(result, msg)
        if args is Ellipsis:
            return super(CallableMeta, self).__getitem__((_TypingEllipsis, result))
        msg = "Callable[[arg, ...], result]: each arg must be a type."
        args = tuple(_type_check(arg, msg) for arg in args)
        parameters = args + (result,)
        return super(CallableMeta, self).__getitem__(parameters)


class Callable(object):
    """Callable type; Callable[[int], str] is a function of (int) -> str.

    The subscription syntax must always be used with exactly two
    values: the argument list and the return type.  The argument list
    must be a list of types or ellipsis; the return type must be a single type.

    There is no syntax to indicate optional or keyword arguments,
    such function types are rarely used as callback types.
    """
    __metaclass__ = CallableMeta
    #def __getitem__(self, params):
    #  pass

    def __new__(cls, *args, **kwds):
        if cls._gorg is Callable:
            raise TypeError("Type Callable cannot be instantiated; "
                            "use a non-abstract subclass instead")
        return _generic_new(cls.__next_in_mro__, cls, *args, **kwds)
