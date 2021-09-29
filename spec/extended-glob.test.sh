#
# This is an OPTION in bash, but not mksh (because the feature originated in
# ksh).
#
# However all extended globs are syntax errors if shopt -s extglob isn't set,
# so I'm not sure what the point of having the option is.  We should always
# parse it?
#
# It's also now a GNU libc extension to glob() and fnmatch() with FNM_EXTMATCH.
# However, this came after shells!  Not sure who uses it.  Does musl have it?
#
# I guess this is handy because it's like *.[ch]... but the extensions can be
# different length.
# 
# Although brace substitution can do this: *.{cc,h}.

# "In addition to the traditional globs (supported by all Bourne-family shells)
# that we've seen so far, Bash (and Korn Shell) offers extended globs, which
# have the expressive power of regular expressions. Korn shell enables these by
# default; in Bash, you must run the command "

# ?(pattern-list): Matches empty or one of the patterns
# *(pattern-list): Matches empty or any number of occurrences of the patterns
# +(pattern-list): Matches at least one occurrences of the patterns
# @(pattern-list): Matches exactly one of the patterns
# !(pattern-list): Matches anything EXCEPT any of the patterns

#### @() matches exactly one of the patterns
shopt -s extglob
touch {foo,bar}.cc {foo,bar,baz}.h
echo @(*.cc|*.h)
## stdout: bar.cc bar.h baz.h foo.cc foo.h

#### ?() matches 0 or 1
shopt -s extglob
touch {foo,bar}.cc {foo,bar,baz}.h foo. foo.hh
echo foo.?(cc|h)
## stdout: foo. foo.cc foo.h

#### *() matches 0 or more
shopt -s extglob
mkdir -p eg1
touch eg1/_ eg1/_One eg1/_OneOne eg1/_TwoTwo eg1/_OneTwo
echo eg1/_*(One|Two)
## stdout: eg1/_ eg1/_One eg1/_OneOne eg1/_OneTwo eg1/_TwoTwo

#### +() matches 1 or more
shopt -s extglob
mkdir -p eg2
touch eg2/_ eg2/_One eg2/_OneOne eg2/_TwoTwo eg2/_OneTwo
echo eg2/_+(One|Two)
## stdout: eg2/_One eg2/_OneOne eg2/_OneTwo eg2/_TwoTwo

#### !(*.h|*.cc) to match everything except C++
shopt -s extglob
mkdir -p extglob2
touch extglob2/{foo,bar}.cc extglob2/{foo,bar,baz}.h \
      extglob2/{foo,bar,baz}.py
echo extglob2/!(*.h|*.cc)
## stdout: extglob2/bar.py extglob2/baz.py extglob2/foo.py

#### Nested extended glob pattern 
shopt -s extglob
mkdir -p eg6
touch eg6/{ab,ac,ad,az,bc,bd}
echo eg6/a@(!(c|d))
echo eg6/a!(@(ab|b*))
## STDOUT:
eg6/ab eg6/az
eg6/ac eg6/ad eg6/az
## END

#### Extended glob patterns with spaces
shopt -s extglob
mkdir -p eg4
touch eg4/a 'eg4/a b' eg4/foo
argv.py eg4/@(a b|foo)
## STDOUT:
['eg4/a b', 'eg4/foo']
## END

#### Filenames with spaces
shopt -s extglob
mkdir -p eg5
touch eg5/'a b'{cd,de,ef}
argv.py eg5/'a '@(bcd|bde|zzz)
## STDOUT:
['eg5/a bcd', 'eg5/a bde']
## END

#### nullglob with extended glob
shopt -s extglob
shopt -s nullglob  # test this too
mkdir eg6
argv.py eg6/@(no|matches)  # no matches
## STDOUT:
[]
## END
## BUG mksh STDOUT:
['eg6/@(no|matches)']
## END


#### glob other punctuation chars (lexer mode)
# mksh sorts them differently
shopt -s extglob
mkdir -p eg5
cd eg5
touch __{'<>','{}','|','#','&&'}
argv.py @('__<>'|__{}|__\||__#|__&&)
## stdout: ['__<>', '__|', '__{}', '__&&', '__#']
## OK mksh stdout: ['__#', '__&&', '__<>', '__{}', '__|']

#### dynamic extglob from variable

# mksh does static parsing so it doesn't like this?
shopt -s extglob
mkdir -p eg3
touch eg3/{foo,bar}
g=eg3/@(foo|bar)
echo $g "$g"  # quoting inhibits globbing
## stdout: eg3/bar eg3/foo eg3/@(foo|bar)
## N-I mksh stdout: eg3/@(foo|bar) eg3/@(foo|bar)
