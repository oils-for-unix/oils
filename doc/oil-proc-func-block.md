---
in_progress: yes
---

Procs, Funcs, and Blocks
========================

<div id="toc">
</div>

## Builtins Can Accept Ruby-Style Blocks

Example of syntax that works:

```
cd / {
  echo $PWD
}
cd / { echo $PWD }
cd / { echo $PWD }; cd / { echo $PWD }
```

Syntax errors:

```
a=1 { echo bad };        # assignments can't take blocks
>out.txt { echo bad };   # bare redirects can't take blocks
break { echo bad };      # control flow can't take blocks
```

Runtime errors

```
local a=1 { echo bad };  # assignment builtins can't take blocks
```

### Caveat: Blocks Are Space Sensitive

```
cd {a,b}  # brace substitution
cd { a,b }  # tries to run command 'a,b', which probably doesn't exist
```

more:

```
echo these are literal braces not a block \{ \}
echo these are literal braces not a block '{' '}'
# etc.
```


### What's Allowed in Blocks?

You can break out with `return`, and it accepts Oil**expressions** (not
shell-like words) (note: not implemented yet).


```
cd {
  # return is for FUNCTIONS.
  return 1 + 2 * 3
}
```

The block can set vars in enclosing scope:

```
setvar('name', 1+2, up=1)
```

They can also get the value:

```
var namespace = evalblock('name', 1+2, up=1)

# _result is set if there was a return statement!

# namespace has all vars except those prefixed with _
var result = namespace->_result
```


* Procs Have Open or Closed Signatures
* Functions Look Like Julia, JavaScript, and Go
* Procs May Accept Block Arguments


TODO:

* Shell vs. Python composition.
* 4 differences in signatures.
* prefix spread ... at call site. Or "rest" parameters.
* @ is "splice" at the call site. Or also "rest" parameters.
* & block. TODO.
* Optional types

Another issue is that I feel like people will tend to prefer funcs because
they're more familiar. But shell composition with proc is very powerful!!!

They have at least two kinds of composition that functions don't have:

http://www.oilshell.org/blog/tags.html?tag=shell-the-good-parts#shell-the-good-parts

So that is another thing that I should write about.


In summary:

* func signatures look like JavaScript, Julia, and Go.
  * named and positional are separated with `;` in the signature.
  * The prefix `...` "spread" operator takes the place of Python's `*args` and `**kwargs`. 
  * There are optional type annotations
* procs are like shell functions
	* but they also allow you to name parameters, and throw errors if the arity
is wrong.
	* and they take blocks.

One issue is that procs take block arguments but not funcs.  This is something
of a syntactic issue.  But I don't think it's that high priority.

---

Here are some complicated examples from the tests.  It's not representative of what real code looks like, but it shows all the features.

proc:

```
proc name-with-hyphen (x, y, @names) {
  echo $x $y
  echo names: @names
}
name-with-hyphen a b c
```

func:

```
shopt -s oil:basic

func f(a, b=0, ...args; c, d=0, ...named) {
  echo __ args: @args
  echo __ named:
  echo @named | sort
  if (named) {
    return [a, b, c, d]
  } else {
    return a + b + c + d
  }
}
var a = [42, 43]
var n = {x: 99, y: 100}

echo ____
echo string $f(0, 1, ...a, c=2, d=3)

# Now get a list back
echo ____
echo array @f(5, 6, ...a, c=7, d=8; ...n)
```


## Blocks

## cd now takes a Ruby-like block

This is enabled by `shopt -s parse_brace`, so the `{}` characters become
special.  Example:

```
cd subdir { 
  ls -l
  echo $PWD
}
cd other/dir { pwd; find . -type f }  # compact one-line syntax
```

Hopefully you can guess what this does!  If not let me know :)

Again, you can try this from HEAD with instructions in the [latest blog
post](http://www.oilshell.org/blog/2019/08/22.html).

This is the first example of many more to come.  I started to document some of the semantics here, but it's not done yet:

https://github.com/oilshell/oil/blob/master/doc/oil-manual.md#builtins

Other builtins that will take blocks:

```
# this replaces an awkward idiom with eval I've seen a lot
shopt -u errexit {
   false
   echo "temporary disable an option"
} 

# generalizes the 'NAME=value command' syntax and the 'env' prefix helps parsing
env PYTHONPATH=. {
  ./foo.py
  ./bar.py
}

# replaces sleep 5 &
fork {  sleep 5 }

# replaces () syntax so we can use it for something else.
wait { echo subshell; sleep 5 }

# probably used for a "syntactic pun" of Python-like "import as" functionality
use lib foo.sh {
  myfunc
  myalias otherfunc
}
```


Yes good question – this hasn’t been addressed by the docs yet, but it will be.

There are two kinds of composition / code units in Oil: proc and func.

- funcs are like Python or JavaScript functions. They accept and return typed data.
- procs are like shell “functions”. They look like an external process, with
argv and an exit code. I think of proc as “procedure” or “proecss”.

- procs are called with a "command line":

    myproc arg1 arg2 arg3

funcs are called with Python/JS-like expressions:

    var x = myfunc(42, 'foo')
    do myfunc(42, 'foo')   # throw away the return value.

This is NOT legal:

    myfunc(42, 'foo')

I will have a whole doc about this, along with some advice on where to use
each. I do expect that it’s one of the more confusing things, but I think it’s
justified because both mechanism are powerful and well-tested. I guess you
kinda have to know shell AND Python to know when to use each.

I use shell as my “main”, if that makes sense. So generally speaking, procs
calls funcs, and funcs won’t call procs as much.

