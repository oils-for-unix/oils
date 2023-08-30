## compare_shells: bash mksh zsh ash
## oils_failures_allowed: 3

#### file redirects with glob args (bash and zsh only)

touch one-bar

echo hi > one-*

cat one-bar

echo escaped > one-\*

cat one-\*

## STDOUT:
hi
escaped
## END
## N-I dash/mksh/ash STDOUT:
escaped
## END

#### file redirect to $var with glob char

touch two-bar

star='*'

echo hi > two-$star
echo status=$?

head two-bar two-\*

## status: 0
## STDOUT:
status=0
==> two-bar <==

==> two-* <==
hi
## END

## BUG bash status: 1
## BUG bash STDOUT:
status=0
==> two-bar <==
hi
## END

#### file redirect that globs to more than one file (bash and zsh only)

touch foo-bar
touch foo-spam

echo hi > foo-*
echo status=$?

head foo-bar foo-spam

## STDOUT:
status=1
==> foo-bar <==

==> foo-spam <==
## END

## N-I dash/mksh/ash STDOUT:
status=0
==> foo-bar <==

==> foo-spam <==
## END

## BUG zsh STDOUT:
status=0
==> foo-bar <==
hi

==> foo-spam <==
hi
## END

#### file redirect with extended glob (bash only)

shopt -s extglob

touch foo-bar

echo hi > @(*-bar|other)
echo status=$?

cat foo-bar

## status: 0
## STDOUT:
status=0
hi
## END

## N-I zsh status: 1
## N-I dash/ash status: 2

## N-I dash/zsh/ash STDOUT:
## END

## BUG mksh status: 0
## BUG mksh STDOUT:
status=0
## END

#### other redirects with glob args

touch 10

exec 10>&1  # open stdout as descriptor 10

# Does this go to stdout?  ONLY bash respects it, not zsh
echo should-not-be-on-stdout >& 1*

echo stdout
echo stderr >&2

## status: 0

## STDOUT:
stdout
## END

## BUG bash STDOUT:
should-not-be-on-stdout
stdout
## END

## N-I dash/zsh status: 127
## N-I dash/zsh STDOUT:
## END
