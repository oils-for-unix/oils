---
in_progress: yes
---

Oil Documentation Toolchain
===========================

The toolchain is based on hand-written Markdown and HTML filters.  See
[lazylex/README.md]().

<div id="toc">
</div>

## Plugins

### Link Shortcuts

This markdown:

```
The [GNU bash shell]($xref:bash)
```

is translated to this HTML:

```
The <a href="$xref:bash">GNU bash shell</a>
```

which is expanded by our plugin to:

```
The <a href="/cross-ref.html#bash">GNU bash shell</a>
```

If the argument is omitted, then the anchor text is used.  For example,

```
<a href="$xref">bash</a>
```

becomes:

```
The <a href="/cross-ref.html#bash">bash</a>
```

List of plugins:

- `$xref:bash` expands to `/cross-ref.html#bash` (shown above)
- `$blog-tag:oil-release` expands to `/blog/tags.html#oil-release`


[bash]($xref)

[oil-release]($blog-tag)

[INSTALL.txt]($oil-src)

[INSTALL.txt]($oil-src:INSTALL.txt)

[interactive-shell/README.md]($blog-code-src)

[issue 11]($issue:11)

[this commit]($oil-commit:a1dad10d53b1fb94a164888d9ec277249ae98b58)

### Syntax Highlighting


Plugins:

`sh-prompt`:

``` sh-prompt
oil$ var x = 'hello world'
oil$ echo $x
hello world
```

`python`:

``` python
x = 42  # comment

def add(y):
  return x + y

print(add(x * 7))
```


### TODO:

- Side-by-side sh and Oil
- Side-by-side PCRE and Eggex
- sh-session - How to replace the data?


A shell session could look like this:

<div shell="sh">

```
$ echo one
$ echo two
```

</div>

Embeddings:

- Embed Image Preview of Web Page?
- Embed Github Commit?
- Graphviz
  - LaTeX (although I don't really use it)


## Help Toolchain

- It splits `help-index.md` and `help.md` into "cards"
- TODO: Render to ANSI

## Code Location

Right now there are several scripts in `devtools/*.py`.  And `build/doc.sh`.

TODO: Move into `doc/`?

