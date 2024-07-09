stdlib/
=======

Ideas for shell functions that could be in here:

- Version comparison: https://github.com/oilshell/oil/issues/683
- An automated way to download the latest version of Oil: https://github.com/oilshell/oil/issues/463
  - Maybe functions to lazily download documentation too?
- `errexit` utilities: https://github.com/oilshell/oil/issues/474

## Notes on Contents

This should be in doc/ref/chap-stdlib.md

    two.sh             # The two functions I actually use
    byo-server-lib.sh  # for using bash to test scripts
                       # you need a client too

YSH

    args.ysh
    testing.ysh  # should these be assertions?

    stream.ysh
    table.ysh

    math.ysh  # abs, max, min - TODO: sum
    list.ysh  # any all sum
    funcs.ysh  # identity - not that useful

    prelude.ysh  # todo pass, hm

## Polyfill ideas

### From Soil - Fix SSH and Bernstein chaining

    ssh $USER@$HOST "$(argv-to-str "$@")"

which is simply:

    ssh $USER@$HOST "$(printf '%q ' "$@")"

Though it would be more convenient as:

    quotefix ssh $USER@$HOST --- "$@"

The --- means you are ending the normal args?


Do we also need one for scp?  On OS X it seems more weird.

### exit 255 for xargs?

That's the special exit code to ABORT, hm.

But I think 'each' will not do this?  We should concentrate on that.


### strict mode

Not sure it makes sense to source anything for this.

    shopt --set strict:all || true 2>&/dev/null
