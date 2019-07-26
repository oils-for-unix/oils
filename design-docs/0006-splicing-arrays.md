True Arrays and Splicing
------------------------

Consequence of oil-word-eval and the !QEFS Problem

### Turn off Word Splitting and Dynamic Globbing

    shopt -s oil-no-split-glob

That changes the behavior of EvalWordSequence2.  It doesn't do dynamic
splitting and globbing.

Then we need static glob:

    shopt -s oil-static-glob

The prefix `oil-` is for options that make the OSH language behave more like
the (hypothetical) Oil language.  Turn on all Oil options like this:

    shopt -s all:oil  # like all:strict

(TODO: Should there be an option for module-level semantic options?  That is,
options can get attach to every function defined in a module, as well as its
top level execution?)

### Arrays and Splicing

Syntax Pragmas change parsing, so they must appear in comments at the beginning
of the module:

    # __syntax__ oil-splice

(The exact syntax is a bit like `from __future__ import print_function` in
Python.)


Then `@a` becomes a 2-character shortcut for the 8-character `"${a[@]}"`:

    array=(ls -l)
    echo @array         # new way
    echo "${array[@]}"  # old way still works

You can also declare arrays using Oil syntax:

    var array = @[ls -l]
    echo @array

Note: homogeneous array literals are `@[ls -l]`, while JSON-like heterogeneous
list literals are `["ls", "-l"]`, `[1, 2, 3, "foo"]`, etc.



### Explicit Splitting and Joining

Since we disabled splitting and globbing, we need a way to explicitly split:


    shell_str='a b c'
    var oil_str = 'a b c'  # same thing

    var a1 = ifssplit(shell_str)
    var a2 = ifssplit(oil_str)

We can reverse by joining:

    array = @[ls -l]
    var s = join(array)
    echo $s              # 'ls -l'

    var s = join(array, ':')
    echo $s              # 'ls:-l'


### Notes on Spelling

Builtin functions We're roughly following Python's style:

    join()
    ifssplit()

#### Alternative considered

ifssplit() has an awkard name because it should be rare:

    split()
    fieldsplit()

Other spellings:

    ifs_split()
    ifsSplit()
    IFSSplit()


    strjoin()
    join(a, ' ')  # for now, ' ' is the default second argument


### Related

Should be on:

    shopt -s strict-array

