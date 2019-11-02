---
in_progress: yes
---

Special Variables
=================

Why have a new spelling?  Because `"$@"` doesn't work well in expression mode.


<div id="toc">
</div>

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

