
## oils_failures_allowed: 14
## compare_shells: bash

#### Don't glob flags on file system with GLOBIGNORE
# This is a bash-specific extension.
expr $0 : '.*/osh$' >/dev/null && exit 99  # disabled until cd implemented
touch _tmp/-n _tmp/zzzzz
cd _tmp  # this fail in osh
GLOBIGNORE=-*:zzzzz  # colon-separated pattern list
echo -* hello zzzz?
## STDOUT:
-* hello zzzz?
## END
## N-I dash/mksh/ash stdout-json: "hello zzzzz"
## status: 0

#### basic star case -> ignore files with txt extension
touch {basic.md,basic.txt}
GLOBIGNORE=*.txt
echo *.*
## STDOUT:
basic.md
## END

#### basic question mark case -> ignore txt files with one char filename
touch {1.txt,10.txt}
GLOBIGNORE=?.txt
echo *.*
## STDOUT:
10.txt
## END

#### multiple patterns -> ignore files with o or h extensions
touch {hello.c,hello.h,hello.o,hello}
GLOBIGNORE=*.o:*.h
echo hello*
## STDOUT:
hello hello.c
## END

#### ignore specific file
mkdir src
touch src/{__init__.py,__main__.py}
GLOBIGNORE='src/__init__.py'
echo src/*
## STDOUT:
src/__main__.py
## END

#### ignore contents of specific directories
mkdir {src,compose,dist,node_modules}
touch src/{a.js,b.js}
touch compose/{base.compose.yaml,dev.compose.yaml}
touch dist/index.js
touch node_modules/package.js
GLOBIGNORE=dist/*:node_modules/*
echo */*
## STDOUT:
compose/base.compose.yaml compose/dev.compose.yaml src/a.js src/b.js
## END

#### find files in subdirectory but not the ignored pattern
mkdir {dir1,dir2}
touch dir1/{a.txt,ignore.txt}
touch dir2/{a.txt,ignore.txt}
GLOBIGNORE=*/ignore*
echo */*
## STDOUT:
dir1/a.txt dir2/a.txt
## END

#### basic range cases
rm -rf _tmp
touch {a,b,c,d,A,B,C,D}
GLOBIGNORE=*[ab]*
echo *
GLOBIGNORE=*[ABC]*
echo *
GLOBIGNORE=*[!ab]*
echo *
## STDOUT:
A B C D c d
D a b c d
a b
## END

#### range cases using character classes
touch {_testing.py,pyproject.toml,20231114.log,.env}
touch 'has space.docx'
GLOBIGNORE=[[:alnum:]]*
echo *.*
GLOBIGNORE=[![:alnum:]]*
echo *.*
GLOBIGNORE=*[[:space:]]*
echo *.*
GLOBIGNORE=[[:digit:]_.]*
echo *.*
## STDOUT:
.env _testing.py
20231114.log has space.docx pyproject.toml
.env 20231114.log _testing.py pyproject.toml
has space.docx pyproject.toml
## END

#### ignore everything
# This pattern appears in public repositories
touch {1.txt,2.log,3.md}
GLOBIGNORE=*
echo *
## STDOUT:
*
## END

#### treat escaped patterns literally
touch {escape-10.txt,escape*.txt}
GLOBIGNORE="escape\*.txt"
echo *.*
## STDOUT:
escape-10.txt
## END

#### resetting globignore reverts to default behaviour
touch reset.txt
GLOBIGNORE=*.txt
echo *.*
GLOBIGNORE=
echo *.*
## STDOUT:
*.*
reset.txt
## END

#### find dotfiles while ignoring . or ..
# globskipdots is enabled by default in bash >=5.2
# for bash <5.2 this pattern is a common way to match dotfiles but not . or ..
shopt -u globskipdots
touch .env
GLOBIGNORE=.:..
echo .*
GLOBIGNORE=
echo .* | sort
## STDOUT:
.env
. .. .env
## END

#### different styles
# each style of "ignore everything" spotted in a public repo
touch image.jpeg
GLOBIGNORE=*
echo *
GLOBIGNORE='*'
echo *
GLOBIGNORE="*"
echo *
GLOBIGNORE=\*
echo *
## STDOUT:
*
*
*
*
## END
