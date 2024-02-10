"""
"""

from typing import List

from _devbuild.gen.yaks_asdl import Token

#_MATCH = re.compile('TODO')


def Lex(s):
    # type: (str) -> List[Token]

    # TODO: use regex

    t = Token('foo.sh', 'echo hi', 5, 1)
    return [t]
