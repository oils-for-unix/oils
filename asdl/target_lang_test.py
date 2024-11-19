#!/usr/bin/env python2
"""target_lang_test.py: test out MyPy-compatible code we generated

Similar to mycpp/demo/target_lang.cc

List of types that could be containers:

syntax.asdl:

  CompoundWord = (List[word_part] parts)
  
  word_part = 
      ...
    | BracedTuple(List[CompoundWord] words)
  
  condition = 
      Shell(List[command] commands)  # if false; true; then echo hi; fi
  
  pat =
    Else
  | Words(List[word] words)
  | YshExprs(List[expr] exprs)
  
  command =
    | CommandList(List[command] children)
  
  re = 
    | Seq(List[re] children)
    | Alt(List[re] children)


runtime.asdl

  part_value = 
    String %Piece

    # "$@" or "${a[@]}" # never globbed or split (though other shells
    # split them)
  | Array(List[str] strs)
  | ExtGlob(List[part_value] part_vals)

  wait_status =
  | Pipeline(List[int] codes)

  trace =
    External(List[str] argv) # sync, needs argv (command.Simple or 'command')

value.asdl

  value =
    | Str(str s)
  
      # Maybe we can add global singletons value::Bool::true and
      # value::Bool::false or something?  They are pointers.
    | Bool(bool b)
  
    # Not sure if we can do anything about these.  Probably should for Int and
    # Float
    | Int(BigInt i)
    | Float(float f)
  
    | BashAssoc(Dict[str, str] d)
    | List(List[value] items)
    | Dict(Dict[str, value] d)
    | Frame(Dict[str, Cell] frame)

Note that this must work:

    with tagswitch(node) as case:
      pass

I think it just needs _type_tag, and then the C++ version will use the GC
header that's BEFORE the object.
"""

from typing import List, Dict


class word_t(object):
    pass


#class CompoundWord('List[int]'):
#class CompoundWord(word_t, 'List[int]'):


#class CompoundWord(List[int]):
class CompoundWord(word_t, List[int]):
    pass


class value_t(object):
    pass


class Dict_(value_t, Dict[str, value_t]):
    pass


class List_(value_t, List[value_t]):
    pass


def main():
    # type: () -> None

    #print(dir(collections))

    # Wow this works
    c = CompoundWord()

    c.append(42)
    print(c)
    print('len %d' % len(c))

    d = Dict_()

    d['key'] = d
    print(d)
    print(len(d))

    mylist = List_()
    print(mylist)
    print(len(mylist))


if __name__ == '__main__':
    main()
