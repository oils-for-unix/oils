Parse Options
-------------

`shopt -s parse_brace` does three things:

- allow builtins like `cd` to take a block (discussed in a [recent thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/cd.20now.20takes.20a.20Ruby-like.20block))
- `if`, `while/until`, `for`, `case` not use curly brace delimiters instead of `then/fi`, `do/done`, etc.  See below.
- To remove confusion, braces must be balanced inside a word.  echo `foo{` is an error.  It has to be `echo foo\{` or `echo 'foo{'`.
  - This is so that the syntax errors are better when you forget a space.
  - In a correct brace expansion, they're always balanced: `echo {andy,bob}@example.com`


Test cases start here:

https://github.com/oilshell/oil/blob/master/spec/oil-options.test.sh#L257

Examples:

```
if test -d / {
  echo one
} elif test -d /tmp {
  echo two
} else {
   echo none
}
# can also be put all on one line

while true {
  echo hi
  break
}

for x in a b c {
  echo $x
}

case $x {
  *.py)
    echo python
    ;;
  *.sh)
    echo shell
    ;;
}
```


What's the motivation for this?  Mainly familiarity: I hear a lot of feedback that nobody can remember how to write an if statement or a for loop in shell.  I believe this syntax is easier to remember, with the possible exception of `case`, which still has some shell legacy.

Spoiler: there will also be **expression**-based variants of each of these constructs:

```
if (x > 0) {
  echo hi
}
while (x > 0) {
  echo hi
}
for (x in @(a b c)) {
  echo $x
}
```

There is probably going to be `switch/case` or `match/case`, but that will
likely come much later!


