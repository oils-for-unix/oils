"""Methods on Obj instances that represent types"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_e, value_t, Obj

from core import error
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch

from typing import Dict, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    pass

_ = log


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
        left_obj = rd.PosValue()
        right = rd.PosValue()

        result = None  # type: Optional[value_t]
        with tagswitch(right) as case:
            if case(value_e.Obj):
                result = value.Bool(False)
            elif case(value_e.List):
                result = value.Bool(True)
            else:
                raise error.TypeErr(right,
                                    'Obj __index__ expected Obj or List',
                                    rd.LeastSpecificLocation())

        return result


if 0:
    """
                index_method = ObjectNone
                if obj.prototype:
                    return None, None

                if index.tag() != value_e.Obj:
                    raise error.TypeErr(index, 'Obj index expected Obj',
                                        blame_loc)

                index = cast(Obj, UP_index)

                # TODO: if index is a List[], then it's not unique?
                # Do we need a unique object type?
                id_str = mylib.hex_lower(j8.ValueId(index))

                cached = obj.d.get(id_str)

                # TODO:
                # - List __index__ allows List[T], but not more?
                # - Dict __index__ allows Dict[K, V], but not more?
                #   - does K, V evaluate to a List?
                #   - or an Obj?
                # 
                # Would be nice to have this in YSH

                if cached is None:

                    left_val = obj.d.get('name')
                    if left_val is None:
                        raise AssertionError()
                    if left_val.tag() != value_e.Str:
                        raise AssertionError()
                    # Should look like

                    # List[Int] -> ['List', 'Int']
                    # Dict[Str, Float] -> ['Dict', 'Str', 'Float']
                    # Dict[Str, List[Int]] -> ['Dict', 'Str', ['List', 'Int']]

                    # where the names are canonical?

                    right_val = index.d.get('name')
                    if right_val is None:
                        raise AssertionError()
                    if right_val.tag() != value_e.Str:
                        raise AssertionError()

                    #raise AssertionError('yo')

                    cached = value.List([left_val, right_val])
                    obj.d[id_str] = cached
                    #log('obj %r', obj.d[id_str])

                return cached
                """
