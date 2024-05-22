## oils_failures_allowed: 1
## compare_shells: bash mksh zsh

# dash and ash don't support $''

#### Unicode escapes \u03bc \U000003bc in $'', echo -e, printf

case $SH in dash|ash) exit ;; esac

echo $'\u03bc \U000003bc'

echo -e '\u03bc \U000003bc'

printf '\u03bc \U000003bc\n'

## STDOUT:
μ μ
μ μ
μ μ
## END

## N-I dash/ash STDOUT:
## END

#### U+10ffff is max code point

case $SH in dash|ash) exit ;; esac

py-repr() {
  python2 -c 'import sys; print repr(sys.argv[1])'  "$@"
}

py-repr $'\U0010ffff'
py-repr $(echo -e '\U0010ffff')
py-repr $(printf '\U0010ffff')

## STDOUT:
'\xf4\x8f\xbf\xbf'
'\xf4\x8f\xbf\xbf'
'\xf4\x8f\xbf\xbf'
## END

## N-I dash/ash STDOUT:
## END

# Unicode replacement char 

## BUG mksh STDOUT:
'\xef\xbf\xbd'
'\xef\xbf\xbd'
'\xf4\x8f\xbf\xbf'
## END

#### 0x00110000 is greater than max code point

case $SH in dash|ash|mksh) exit ;; esac

py-repr() {
  python2 -c 'import sys; print repr(sys.argv[1])'  "$@"
}

py-repr $'\U00110000'
py-repr $(echo -e '\U00110000')
py-repr $(printf '\U00110000')


## status: 2
## STDOUT:
## END

## BUG dash/ash/mksh status: 0

## BUG bash/zsh status: 0
## BUG bash/zsh STDOUT:
'\xf4\x90\x80\x80'
'\xf4\x90\x80\x80'
'\xf4\x90\x80\x80'
## END



