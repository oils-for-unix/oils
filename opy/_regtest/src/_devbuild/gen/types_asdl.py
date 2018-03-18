from asdl import const  # For const.NO_INTEGER
from asdl import py_meta
from osh.meta import TYPES_TYPE_LOOKUP as TYPE_LOOKUP

class bool_arg_type_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('bool_arg_type')

bool_arg_type_e.Undefined = bool_arg_type_e(1, 'Undefined')
bool_arg_type_e.Path = bool_arg_type_e(2, 'Path')
bool_arg_type_e.Int = bool_arg_type_e(3, 'Int')
bool_arg_type_e.Str = bool_arg_type_e(4, 'Str')
bool_arg_type_e.Other = bool_arg_type_e(5, 'Other')

class redir_arg_type_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('redir_arg_type')

redir_arg_type_e.Path = redir_arg_type_e(1, 'Path')
redir_arg_type_e.Desc = redir_arg_type_e(2, 'Desc')
redir_arg_type_e.Here = redir_arg_type_e(3, 'Here')

class lex_mode_e(py_meta.SimpleObj):
  ASDL_TYPE = TYPE_LOOKUP.ByTypeName('lex_mode')

lex_mode_e.NONE = lex_mode_e(1, 'NONE')
lex_mode_e.COMMENT = lex_mode_e(2, 'COMMENT')
lex_mode_e.OUTER = lex_mode_e(3, 'OUTER')
lex_mode_e.DBRACKET = lex_mode_e(4, 'DBRACKET')
lex_mode_e.SQ = lex_mode_e(5, 'SQ')
lex_mode_e.DQ = lex_mode_e(6, 'DQ')
lex_mode_e.DOLLAR_SQ = lex_mode_e(7, 'DOLLAR_SQ')
lex_mode_e.ARITH = lex_mode_e(8, 'ARITH')
lex_mode_e.EXTGLOB = lex_mode_e(9, 'EXTGLOB')
lex_mode_e.VS_1 = lex_mode_e(10, 'VS_1')
lex_mode_e.VS_2 = lex_mode_e(11, 'VS_2')
lex_mode_e.VS_ARG_UNQ = lex_mode_e(12, 'VS_ARG_UNQ')
lex_mode_e.VS_ARG_DQ = lex_mode_e(13, 'VS_ARG_DQ')
lex_mode_e.BASH_REGEX = lex_mode_e(14, 'BASH_REGEX')
lex_mode_e.BASH_REGEX_CHARS = lex_mode_e(15, 'BASH_REGEX_CHARS')

