#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.typed_arith_asdl import arith_expr_t
from asdl import tdop
from asdl import typed_arith_parse  # module under test

from typing import Callable, Optional, TYPE_CHECKING


# Type alias
if TYPE_CHECKING:
  ParseFunc = Callable[[str, Optional[str]], arith_expr_t]


def _assertParseError(make_parser, s, error_substring=''):
  # type: (Callable[[str], tdop.Parser], str, str) -> None
  p = make_parser(s)
  try:
    node = p.Parse()
  except tdop.ParseError as e:
    err = str(e)
    if error_substring in err:
      print('got expected error for %s: %s' % (s, err))
    else:
      raise AssertionError('Expected %r to be in %r' % (error_substring, err))
  else:
    raise AssertionError('%r should have failed' % s)


def TestArith(t_parse):
  # type: (ParseFunc) -> None
  t_parse('1+2+3', '(+ (+ 1 2) 3)')
  t_parse('1+2*3', '(+ 1 (* 2 3))')
  t_parse('4*(2+3)', '(* 4 (+ 2 3))')
  t_parse('(2+3)*4', '(* (+ 2 3) 4)')
  t_parse('1<2', '(< 1 2)')
  t_parse('x=3', '(= x 3)')
  t_parse('x = 2*3', '(= x (* 2 3))')
  t_parse('x = y', '(= x y)')

  t_parse('x*y - y*z', '(- (* x y) (* y z))')
  t_parse('x/y - y%z', '(- (/ x y) (% y z))')

  t_parse("x = y", "(= x y)")
  t_parse('2 ** 3 ** 2', '(** 2 (** 3 2))')
  t_parse('a = b = 10', '(= a (= b 10))')

  t_parse('x = ((y*4)-2)', '(= x (- (* y 4) 2))')

  t_parse('x - -y', '(- x (- y))')
  t_parse("-1 * -2", "(* (- 1) (- 2))")
  t_parse("-x * -y", "(* (- x) (- y))")
  t_parse('x - -234', '(- x (- 234))')

  # Python doesn't allow this
  t_parse('x += y += 3', '(+= x (+= y 3))')

  # This is sort of nonsensical, but bash allows it.  The 1 is discarded as
  # the first element of the comma operator.
  t_parse('x[1,2]', '(get x (, 1 2))')

  # Python doesn't have unary +
  t_parse('+1 - +2', '(- (+ 1) (+ 2))')

  # LHS
  t_parse('f[x] += 1', '(+= (get f x) 1)')


def TestBitwise(t_parse):
  # type: (ParseFunc) -> None
  t_parse("~1 | ~2", "(| (~ 1) (~ 2))")
  t_parse("x & y | a & b", "(| (& x y) (& a b))")
  t_parse("~x ^ y", "(^ (~ x) y)")
  t_parse("x << y | y << z", "(| (<< x y) (<< y z))")

  t_parse("a ^= b-1", "(^= a (- b 1))")


def TestLogical(t_parse):
  # type: (ParseFunc) -> None
  t_parse("a && b || c && d", "(|| (&& a b) (&& c d))")
  t_parse("!a && !b", "(&& (! a) (! b))")
  t_parse("a != b && c == d", "(&& (!= a b) (== c d))")

  t_parse("a > b ? 0 : 1", "(? (> a b) 0 1)")
  t_parse("a > b ? x+1 : y+1", "(? (> a b) (+ x 1) (+ y 1))")

  t_parse("1 ? true1 : 2 ? true2 : false", "(? 1 true1 (? 2 true2 false))")
  t_parse("1 ? true1 : (2 ? true2 : false)", "(? 1 true1 (? 2 true2 false))")

  t_parse("1 ? (2 ? true : false1) : false2", "(? 1 (? 2 true false1) false2)")
  t_parse("1 ? 2 ? true : false1 : false2", "(? 1 (? 2 true false1) false2)")

  # Should have higher precedence than comma
  t_parse("x ? 1 : 2, y ? 3 : 4", "(, (? x 1 2) (? y 3 4))")


def TestUnary(t_parse):
  # type: (ParseFunc) -> None
  t_parse("!x", "(! x)")
  t_parse("x--", "(post-- x)")
  t_parse("x[1]--", "(post-- (get x 1))")

  t_parse("--x", "(-- x)")
  t_parse("++x[1]", "(++ (get x 1))")

  t_parse("!x--", "(! (post-- x))")
  t_parse("~x++", "(~ (post++ x))")

  t_parse("x++ - y++", "(- (post++ x) (post++ y))")

  t_parse("++x - ++y", "(- (++ x) (++ y))")

  #
  # 1.   x++  f()  x[]  left associative
  #                     f(x)[1]++  means
  #                     (++ (get (call f x) 1))
  # 2.   ++x  + - ! ~   right associative
  #                     -++x means (- (++ x))


def TestArrays(t_parse):
  # type: (ParseFunc) -> None
  """Shared between shell, oil, and Python."""
  t_parse('x[1]', '(get x 1)')
  t_parse('x[a+b]', '(get x (+ a b))')
  t_parse('x[1:2]', 'SLICE')


def TestComma(t_parse):
  # type: (ParseFunc) -> None
  t_parse('x=1,y=2,z=3', '(, (= x 1) (= y 2) (= z 3))')


def TestFuncCalls(t_parse):
  # type: (ParseFunc) -> None
  t_parse('x = y(2)*3 + y(4)*5', '(= x (+ (* (call y 2) 3) (* (call y 4) 5)))')

  t_parse('x(1,2)+y(3,4)', '(+ (call x 1 2) (call y 3 4))')
  t_parse('x(a,b,c[d])', '(call x a b (get c d))')
  t_parse('x(1,2)*j+y(3,4)*k+z(5,6)*l',
          '(+ (+ (* (call x 1 2) j) (* (call y 3 4) k)) (* (call z 5 6) l))')
  t_parse('print(test(2,3))', '(call print (call test 2 3))')
  t_parse('print("x")', '(call print x)')
  t_parse('min(255,n*2)', '(call min 255 (* n 2))')
  t_parse('c = pal[i*8]', '(= c (get pal (* i 8)))')


def TestErrors(p):
  # type: (Callable[[str], tdop.Parser]) -> None
  _assertParseError(p, '}')
  _assertParseError(p, ']')

  _assertParseError(p, '{')  # depends on language

  _assertParseError(p, "x+1 = y", "Can't assign")
  _assertParseError(p, "(x+1)++", "Can't assign")

  # Should be an EOF error
  _assertParseError(p, 'foo ? 1 :', 'Unexpected end')

  _assertParseError(p, 'foo ? 1 ', 'expected :')
  _assertParseError(p, '%', "can't be used in prefix position")

  error_str = "can't be used in prefix"
  _assertParseError(p, '}')
  _assertParseError(p, '{')
  _assertParseError(p, ']', error_str)

  _assertParseError(p, '1 ( 2', "can't be called")
  _assertParseError(p, '(x+1) ( 2 )', "can't be called")
  #_assertParseError(p, '1 ) 2')

  _assertParseError(p, '1 [ 2 ]', "can't be indexed")


def t_parse(s,  # type: str
            expected=None,  # type: Optional[str]
            ):
  # type: (...) -> arith_expr_t
  p = typed_arith_parse.MakeParser(s)
  tree = p.Parse()

  print()
  print('---')
  print()

  print(s)
  print()
  print(tree)

  from asdl import format as fmt
  from mycpp import mylib

  ast_f = fmt.DetectConsoleOutput(mylib.Stdout())
  p_node = tree.AbbreviatedTree()
  fmt.PrintTree(p_node, ast_f)

  #v = PrettyPrinter()
  #v.Visit(tree)

  #print('%-40s %s' % (s, sexpr))
  return tree


def main():
  # type: () -> None

  # TODO: Enable once we switch to MyPy
  if 0:
    return

  p = typed_arith_parse.MakeParser

  TestArith(t_parse)
  TestBitwise(t_parse)
  TestLogical(t_parse)
  TestUnary(t_parse)
  TestArrays(t_parse)
  TestFuncCalls(t_parse)
  TestComma(t_parse)
  TestErrors(p)


if __name__ == '__main__':
  main()
