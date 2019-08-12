shopt -s namespaces and the 'use' builtin
-----------------------------------------

### shopt -s namespaces

Normally, shell functions or "procs" live in namespace separte from variables
(`self.procs` in Executor).

When `shopt -s namespaces` is enabled, both "procs" and Oil functions are
entered in 'mem'.  

(NOTE: completion has to be changed to look in types.)

Example:

    f() {
      echo 'this is a proc (a shell function)'
    }
    f

    echo $f  # this is a variable, not a proc

    shopt -s namespaces
    f() { echo 'shadows the old f' }

    repr f
    echo $f  # should say 'Function' types can't be used in words

### Declarations

These are for external tools.  They are no-ops at runtime.

#### use bin

- Intended to be used by packaging tools.


    # The _ is optional, to delimit
    use bin _ grep sed awk

    # maybe:
    use bin __ grep sed awk

    push array __ a b c

#### use env

- Intended to be used by static checkers.
  - If `set -o nounset`, then all variables should be statically known.
  - And as long as names are explicit -- A good reason to disallow `import *`!

    use env __ LOGNAME PYTHONPATH

Vars like $PATH and $PWD don't have to be declared.  (TODO: osh could print a
list of them.)


#### use lib

Like `source`, but respects namespaces.


    use lib foo.sh   # __ is optional here

    use lib __ foo.sh bar.sh baz.sh


    use lib foo.sh

    use foo.sh  # shortcut for use lib.sh

    # Parse this as a block, with simple_command?

    use foo.sh { 
      log
      p_die
      e_die
      myFunc  # not just 'procs' can be imported
      MyType
    }

    use foo.sh { 
      log
      p_die
      e_die
    }

    use foo.sh { 
      mylog log
      p_alias p_die
      e_alias e_die
      funcAlias myFunc
      TypeAlias MyType
    }

    use foo.sh { 
      mylog = log
      p_alias = p_die
      e_alias = e_die
      funcAlias = myFunc
      TypeAlias = MyType

      # This is a little confusing then
      func1
      func2
    }
    use foo.sh  # foo myproc, foo.myfunc() or foo::myfunc()

    # short versions
    use foo.sh { log; p_die; e_die }
    use foo.sh { mylog log; p_alias p_die }

