---
default_highlighter: oils-sh
in_progress: true
---

Block Literals
==============

Procs are shell like-functions, but they can have declared parameters, and lack
dynamic scope.

    proc p(name, age) {
      echo "$name is $age years old"
    }

    p alice 42  # => alice is 42 years old

Blocks are fragments of code within `{ }` that can be passed to builtins (and
eventually procs):

    cd /tmp {
      echo $PWD  # prints /tmp
    }
    echo $PWD  # prints original dir

- See [YSH Idioms](idioms.html) for examples of procs.

<!--

- Block literals are  a syntax for unevaluated code like `cd /tmp { echo $ PWD
  }`. They are instances of "quotation type" `value.Command`.  The  `{ }`
  syntax is niec for passing to blocks to procs, but they can be passed to
  funcs as well.

You don't define blocks.  Blocks are data types.

-->

<div id="toc">
</div>

## Syntax

These forms work:

    cd / {
      echo $PWD
    }
    cd / { echo $PWD }
    cd / { echo $PWD }; cd / { echo $PWD }

These are syntax errors:

    a=1 { echo bad };        # assignments can't take blocks
    >out.txt { echo bad };   # bare redirects can't take blocks
    break { echo bad };      # control flow can't take blocks

Runtime error:

    local a=1 { echo bad };  # assignment builtins can't take blocks

Caveat: Blocks Are Space Sensitive

    cd {a,b}  # brace substitution
    cd { a,b }  # tries to run command 'a,b', which probably doesn't exist

Quoting of `{ }` obeys the normal rules:

    echo 'literal braces not a block' \{ \}
    echo 'literal braces not a block' '{' '}'

## Semantics 

TODO: This section has to be implemented and tested.

### Use `eval` to evaluate a block

TODO: use `eval`


    proc p(&block) {
      echo '>'
      $block    # call it?
                # or maybe just 'block' -- it's a new word in the "proc" namespace?
      echo '<'
    }

    # Invoke it
    p {
      echo 'hello'
    }
    # Output:
    # >
    # hello
    # <

### Hay Config Blocks

TODO

### Errors

Generally, errors occur *inside* blocks, not outside:

    cd /tmp {
       cp myfile /bad   # error happens here
       echo 'done'
    }                   # not here

### Control Flow

- `break` and `continue` are disallowed inside blocks.
- You can exit a block early with `return` (not the enclosing function).
- `exit` is identical: it exits the program.

### 16 Use Cases for Blocks

See 16 use cases on the blog: [Sketches of YSH
Features](https://www.oilshell.org/blog/2023/06/ysh-features.html).

<!--
### Configuration Files

Evaluates to JSON (like YAML and TOML):

    server foo {
      port = 80
    }

And can also be serialized as command line flags.

Replaces anti-patterns:

- Docker has shell
- Ruby DSLs like chef have shell
- similar to HCL I think, and Jsonnet?  But it's IMPERATIVE.  Probably.  It
  might be possible to do dataflow variables... not sure.  Maybe x = 1 is a
  dataflow var?

### Awk Dialect

    BEGIN {
      end
    }

    when x {
    }

### Make Dialect

    rule foo.c : foo.bar {
      cc -o out @srcs
    }

### Flag Parsing to replace getopts

Probably use a block format.  Compare with Python's optparse.o

See issue.

### Unit Tests

Haven't decided on this yet.

    check {
    }
-->

