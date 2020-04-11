Doc Comments
------------

Doc comments can be attached to functions like this:

    deploy() {
      ### Copy the binary to a versioned directory and restart

      echo 'deploying ...'
    }

This is of course backward-compatible with existing shells.

These comments will be surfaced as **descriptions** in interactive completion.

### Other Sources of Completion Descriptions

- fishcomp builtin
- the `help=` text for builtins themselves

