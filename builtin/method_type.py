"""Methods on Obj instances that represent types"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_e, value_t, Obj

from core import error
from core import vm
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log, tagswitch, str_switch

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
    This maintains the invariants:

        List[Int] is List[Int]
        List[Str] is List[Str]

    i.e. 2 evaluations always yield the same object
    """

    def __init__(self):
        # type: () -> None
        self.unique_instances = {}  # type: Dict[str, Obj]

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        val = self._Call(rd)
        if val is None:
            raise error.Expr(
                'Obj __index__ method detected a broken type Obj invariant',
                rd.LeastSpecificLocation())
        return val

    def _Call(self, rd):
        # type: (typed_args.Reader) -> Optional[value_t]
        left_obj = rd.PosObj()
        right = rd.PosValue()
        rd.Done()

        left_name = _GetStringField(left_obj, 'name')
        if left_name is None:
            return None  # all type objects should have 'name'

        UP_right = right

        objects = []  # type: List[Obj]
        with tagswitch(right) as case2:
            if case2(value_e.Obj):
                right = cast(Obj, UP_right)
                objects.append(right)

            elif case2(value_e.List):
                right = cast(value.List, UP_right)
                for i, val in enumerate(right.items):
                    if val.tag() != value_e.Obj:
                        # List[Str, 3] is invalid
                        return None
                    objects.append(cast(Obj, val))
            else:
                raise error.TypeErr(
                    right, 'Obj __index__ method expected Obj or List',
                    rd.LeastSpecificLocation())

        with str_switch(left_name) as case:
            if case("List"):
                expected_params = 1
            elif case("Dict"):
                expected_params = 2
            else:
                expected_params = 0

        actual = len(objects)
        if expected_params != actual:
            raise error.Expr(
                'Obj __index__ method expected %d params, got %d' %
                (expected_params, actual), rd.LeastSpecificLocation())

        buf = mylib.BufWriter()
        buf.write(left_name)
        buf.write('[')

        for i, r in enumerate(objects):
            if i != 0:
                buf.write(',')

            #log('OBJ %s', r)

            r_unique_id = _GetStringField(r, 'unique_id')
            if r_unique_id is not None:
                buf.write(r_unique_id)
            else:
                r_name = _GetStringField(r, 'name')
                if r_name is None:
                    # every param object should have either:
                    # 'name' - type object
                    # 'unique_id' - parameterized type object
                    return None
                buf.write(r_name)

        buf.write(']')

        unique_id = buf.getvalue()
        obj_with_params = self.unique_instances.get(unique_id)
        if obj_with_params is None:
            # These are parameterized type objects
            props = {
                'unique_id': value.Str(unique_id),
                #'children': value.List(children)
            }  # type: Dict[str, value_t]
            obj_with_params = Obj(None, props)
            self.unique_instances[unique_id] = obj_with_params

        return obj_with_params
