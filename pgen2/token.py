"""Token constants (from "token.h")."""

#  Taken from Python (r53757) and modified to include some tokens
#   originally monkeypatched in by pgen2.tokenize

#--start constants--
ENDMARKER = 0
NAME = 1
NUMBER = 2
STRING = 3
NEWLINE = 4
INDENT = 5
DEDENT = 6
LPAR = 7
RPAR = 8
LSQB = 9
RSQB = 10
COLON = 11
COMMA = 12
SEMI = 13
PLUS = 14
MINUS = 15
STAR = 16
SLASH = 17
VBAR = 18
AMPER = 19
LESS = 20
GREATER = 21
EQUAL = 22
DOT = 23
PERCENT = 24
BACKQUOTE = 25
LBRACE = 26
RBRACE = 27
EQEQUAL = 28
NOTEQUAL = 29
LESSEQUAL = 30
GREATEREQUAL = 31
TILDE = 32
CIRCUMFLEX = 33
LEFTSHIFT = 34
RIGHTSHIFT = 35
DOUBLESTAR = 36
PLUSEQUAL = 37
MINEQUAL = 38
STAREQUAL = 39
SLASHEQUAL = 40
PERCENTEQUAL = 41
AMPEREQUAL = 42
VBAREQUAL = 43
CIRCUMFLEXEQUAL = 44
LEFTSHIFTEQUAL = 45
RIGHTSHIFTEQUAL = 46
DOUBLESTAREQUAL = 47
DOUBLESLASH = 48
DOUBLESLASHEQUAL = 49
AT = 50
ATEQUAL = 51
OP = 52
COMMENT = 53
NL = 54
RARROW = 55
AWAIT = 56
ASYNC = 57
ERRORTOKEN = 58
N_TOKENS = 59
NT_OFFSET = 512
#--end constants--

tok_name = {}
for _name, _value in list(globals().items()):
    if type(_value) is type(0):
        tok_name[_value] = _name


def ISTERMINAL(x):
    # type: (int) -> bool
    return x < NT_OFFSET

def ISNONTERMINAL(x):
    # type: (int) -> bool
    return x >= NT_OFFSET

def ISEOF(x):
    # type: (int) -> bool
    return x == ENDMARKER


# Map from operator to number.  NOTE: This was moved here from
# pgen2/grammar.py.  Oil doesn't need this; only parsers that use Python's
# tokenizer (like pgen itself) need it.

opmap_raw = """
( LPAR
) RPAR
[ LSQB
] RSQB
: COLON
, COMMA
; SEMI
+ PLUS
- MINUS
* STAR
/ SLASH
| VBAR
& AMPER
< LESS
> GREATER
= EQUAL
. DOT
% PERCENT
` BACKQUOTE
{ LBRACE
} RBRACE
@ AT
@= ATEQUAL
== EQEQUAL
!= NOTEQUAL
<> NOTEQUAL
<= LESSEQUAL
>= GREATEREQUAL
~ TILDE
^ CIRCUMFLEX
<< LEFTSHIFT
>> RIGHTSHIFT
** DOUBLESTAR
+= PLUSEQUAL
-= MINEQUAL
*= STAREQUAL
/= SLASHEQUAL
%= PERCENTEQUAL
&= AMPEREQUAL
|= VBAREQUAL
^= CIRCUMFLEXEQUAL
<<= LEFTSHIFTEQUAL
>>= RIGHTSHIFTEQUAL
**= DOUBLESTAREQUAL
// DOUBLESLASH
//= DOUBLESLASHEQUAL
-> RARROW
"""

import sys
this_module = sys.modules[__name__]
opmap = {}
for line in opmap_raw.splitlines():
    if line:
        op, name = line.split()
        opmap[op] = getattr(this_module, name)
