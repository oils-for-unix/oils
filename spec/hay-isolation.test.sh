#### Turn off external binaries with shvar PATH='' {}
shopt --set parse_brace parse_proc

echo hi > file

# Note: this CACHES the lookup, so shvar has to clear cache when modifying it
cp -v file /tmp >&2
echo status=$?

# TODO: implement this, and call it whenever shvar mutates PATH?
# what about when PATH is mutated?   No leave it out for now.

# hash -r  # clear the cache, no longer necessary

shvar PATH='' {
  cp -v file /tmp
  echo status=$?

  # this also doesn't work
  command cp -v file /tmp
  echo status=$?
}

# Now it's available again
cp -v file /tmp >&2
echo status=$?

## STDOUT:
status=0
status=127
status=127
status=0
## END

#### More shvar PATH=''
shopt --set parse_brace command_sub_errexit parse_proc

shvar PATH='' {
  ( cp -v file /tmp >&2 )
  echo status=$?

  forkwait {
    cp -v file /tmp >&2
  }
  echo status=$?

  try {
    true $(cp -v file /tmp >&2)
  }
  echo _status $_status
}

## STDOUT:
status=127
status=127
_status 127
## END

