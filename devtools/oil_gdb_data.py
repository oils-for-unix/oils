#!/usr/bin/env python2
"""
oil_gdb_data.py
"""

asdl_types = {
    'runtime_asdl::part_value_t': {
        1: 'runtime_asdl::part_value__String',
        2: 'runtime_asdl::part_value__Array',
    },
    'runtime_asdl::value_t': {
        1: 'runtime_asdl::value__Undef',
        2: 'runtime_asdl::value__Str',
        3: 'runtime_asdl::value__Int',
        4: 'runtime_asdl::value__MaybeStrArray',
        5: 'runtime_asdl::value__AssocArray',
    },
}

