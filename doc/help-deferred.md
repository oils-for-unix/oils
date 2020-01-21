<!-- Cut out of Oil 2020 -->

<h2 id="command">
  Command Language (<a class="group-link" href="help.html#command">command</a>)
</h2>

```oil-help-index
  [Oil Keywords]  func   do   pass
X [Coil Keywords] const   try   catch   throw   switch   match
                  data   enum   module   interface   namespace
```

<h2 id="expr">
  Oil Expression Language (<a class="group-link" href="help.html#expr">expr</a>)
</h2>

```oil-help-index
  [Data Types]    Str           r'\'   c'\n'   "$var"   X multiline r""" c'''
                  X Symbol      %foo
                  Null          null
                  Bool          true false
                  Int           1_000_000  0b0100  0xFF  0o377  \n  \\  \u0100
                  Float         3.14   6.022e+23
                  Array[]       @(ls -l)  @[T F F]  @[1 2 3]  @[1.5 2.5] 
                  Tuple[]       ()  tup(42)  (42, "foo")
                  List          [1, 'str', false]  (for JSON compatibility)
                  Dict[]        {name: 'oil'}  {['name']: 'oil'}  {name}
                  Regex         /d+/
                  X Func        fn(x) x+1   func(x) { return x+1 }
                  X Buf         file-like, mutable string
  [Operators]     unary         -a
                  binary        a+b   base^exp  a xor b  p div q  0:n
                  ternary       a if cond else b
                  subscript     a[b, c]   a[start:end]
                  X chain       pass a => f(y, z) => var new
                  getattr       d->key is like d['key'] or d.key
                  scope-attr    module::name
                  genexp   listcomp   X dictcomp
  [Functions] 
                  func-decl     func inc(p, p2=0; n=0, ...named) { echo hi }
```

<h2 id="word">
  Word Language (<a class="group-link" href="help.html#word">word</a>)
</h2>

```oil-help-index
  [Oil Word]      expr-sub      $[f(x)]  $[obj.attr]  $[d->key]  $[obj[index]]
```

<h2 id="builtin">
  Builtin Commands (<a class="group-link" href="help.html#builtin">builtin</a>)
</h2>

```oil-help-index
  [Oil Builtins]  X dirname   X basename optimizations
```

<h2 id="lib">
  Oil Libraries (<a class="group-link" href="help.html#lib">lib</a>)
</h2>

```oil-help-index
  [Collections]   min()   max()   any()   all()   tup()  
                  sorted()   reversed()
  [Math]          sum()   abs()
  [Iteration]     range()   enumerate()   zip()
  [libc]          read(n)             better than read -n, no short reads?
                  posix::read()       raw bindings?
```
