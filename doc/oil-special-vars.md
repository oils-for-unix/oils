Special Variables
=================

## Special Variables

- `ARGV` instead of `"$@"`

In command mode:

```
f() {
  echo @ARGV
}
f 'foo bar' 'spam eggs'
```

In expression mode:

```
var length = len(ARGV)
var s = sorted(ARGV)
```

