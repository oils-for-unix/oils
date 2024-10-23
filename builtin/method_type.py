"""Methods on Obj instances that represent types"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_e, value_t, Obj

from core import error
from core import vm
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log, tagswitch

from typing import Dict, List, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    pass

_ = log


def _GetStringField(obj, field_name):
    # type: (Obj, str) -> Optional[str]

    val = obj.d.get(field_name)

    # This could happen if a user attaches this BuiltinFunc to another
    # Object?  A non-type object.  Or the user can mutate the type object.
    if val is None:
        return None
    if val.tag() != value_e.Str:
        return None
    return cast(value.Str, val).s


class Index__(vm._Callable):
    """
    These are similar:

        var cmd = ^(echo hi)
        call io->eval(cmd)

    Also give the top namespace

        call io->evalToDict(cmd)

    The CALLER must handle errors.
    """

    def __init__(self):
        # type: () -> None
        self.cache = {}  # type: Dict[str, Obj]

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        left_obj = rd.PosObj()
        right = rd.PosValue()

        left_name = _GetStringField(left_obj, 'name')
        if left_name is None:
            raise AssertionError()

        UP_right = right
        result = None  # type: Optional[value_t]

        objects = []  # type: List[Obj]
        with tagswitch(right) as case:
            if case(value_e.Obj):
                right = cast(Obj, UP_right)
                objects.append(right)

            elif case(value_e.List):
                right = cast(value.List, UP_right)
                for i, val in enumerate(right.items):
                    if val.tag() != value_e.Obj:
                        raise AssertionError()
                    objects.append(cast(Obj, val))
            else:
                raise error.TypeErr(right,
                                    'Obj __index__ expected Obj or List',
                                    rd.LeastSpecificLocation())

        buf = mylib.BufWriter()
        buf.write(left_name)
        buf.write('[')

        for i, r in enumerate(objects):
            if i != 0:
                buf.write(',')

            #log('OBJ %s', r)

            r_unique_id = _GetStringField(r, 'unique_id')
            if r_unique_id:
                buf.write(r_unique_id)
            else:
                r_name = _GetStringField(r, 'name')
                if r_name is None:
                    log('BAD %s', r)
                    raise AssertionError()
                buf.write(r_name)
        buf.write(']')

        children = []  # type: List[value_t]

        unique_id = buf.getvalue()
        obj_with_params = self.cache.get(unique_id)
        if obj_with_params is None:
            # These are parameterized type objects
            props = {
                'unique_id': value.Str(unique_id),
                #'children': value.List(children)
            }  # type: Dict[str, value_t]
            obj_with_params = Obj(None, props)
            self.cache[unique_id] = obj_with_params
        return obj_with_params
