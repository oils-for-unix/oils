## oils_failures_allowed: 4

#### compexport

compexport -c 'hay'

## STDOUT:
'haynode '
'hay '
## END

#### compexport with newline in command

# TODO: reject line buf?

compexport -c $'hay\nec'


## STDOUT:
TODO: reject
## END

#### filenames are completed

touch foo bar baz

compexport -c $'echo ba'

# Is the order reversed?
# Does GNU readline always sort them?

## STDOUT:
echo baz 
echo bar 
z
## END

#### -o default is an "else action", when zero are shown

touch file1 file2

echo '-- nothing registered'
compexport -c 'GIT '

__git() {
  #argv.py "$@"
  COMPREPLY=(foo bar)
}

complete -F __git GIT

echo '-- func'
compexport -c 'GIT '

complete -F __git -o default GIT
echo '-- func default'
compexport -c 'GIT '

__git() {
  # don't show anything
  true
}

# have to RE-REGISTER after defining function!  Hm
complete -F __git -o default GIT

echo '-- empty func default'
compexport -c 'GIT '

# Is the order reversed?
# Does GNU readline always sort them?

## STDOUT:
git
## END

# TODO:
# --begin --end  
# --table ?  For mulitiple completions
# compatible with -C ?
# --trace - show debug_f tracing on stderr?  Would be very nice!

#### git completion space issue

. $REPO_ROOT/testdata/completion/git-completion.bash
echo status=$?

#complete

# Bug: it has an extra \ on it
compexport -c 'git ch'

## status: 0
## STDOUT:
## END

#### Complete Filenames with bad characters

touch hello
touch $'hi\xffthere'

compexport -c 'echo h'
## STDOUT:
## END

#### Complete Command with bad characters

touch foo fooz

compexport -c "echo \$'bad \\xff byte' f"

## STDOUT:
## END

