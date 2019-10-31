---
in_progress: yes
---

Oil Word Language Extensions
============================

<div id="toc">
</div>


## Inline function Calls

### That Return Strings

```
echo $stringfunc(x, y)
```

NOTE: `"__$stringfunc(x, y)__"` doesn't work.  Do this instead:

```
var s = stringfunc(x, y)
echo "__$s__"
```

### That Return Arrays

```
cc -o foo -- @arrayfunc(x, y)
```


```
@array
```


Conclusion: I think the conservative approach is better.

This is the same discussion as `$f(x) vs `$(f(x))` on the [inline function calls thread](https://oilshell.zulipchat.com/#narrow/stream/121540-oil-discuss/topic/Inline.20function.20calls.20implemented).

We only want to interpolate **vars** and **functions**.  Arbitrary expressions aren't necessary.

In summary:

- `echo foo=$x` interpolates a variable into a unquoted word
- `echo foo=$f(x)` interpolates a call returning a string into an unquoted word
- `echo "foo=$[x] 1 2 3"` interpolates a variable into a double quoted string
- `echo "foo=${x} 1 2 3"` -- older, same
- `echo "foo=$[f(x)] 1 2 3"` interpolates a call returning a string into a double quoted string

OK I'm pretty happy with this explanation!    Shell is messy but Oil is bringing some order to it :)


---

And then for completeness we also have:

- `echo @x`  interpolates an array into a command
- `echo @f(x)` interpolates a function returning an array into a command

## Unimplemented

`${x|html}`

`${x %.3f}`

