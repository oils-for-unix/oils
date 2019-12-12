# Stripped down version of typing.py for runtime support only!
#
# We got rid of runtime dependences on collections.py, copy.py, etc.
#
# MyPy has its own version of this, since it's written in Python 3.  We don't
# need any support at runtime.
#
# If you need to define a type alias, do something like:
#
# if TYPE_CHECKING:
#   NullFunc = Callable[[int, int], int]

TypingMeta = None
TypeVar = None
_ForwardRef = None
List = None
Sequence = None
Tuple = None
Optional = None
Union = None
IO = None
Dict = None
Iterator = None
Any = None
NoReturn = None
Callable = None
Counter = None  # for ID_HIST

TYPE_CHECKING = False


def cast(typ, val):
    """Cast a value to a type.

    This returns the value unchanged.  To the type checker this
    signals that the return value has the designated type, but at
    runtime we intentionally don't check anything (we want this
    to be as fast as possible).
    """
    return val
