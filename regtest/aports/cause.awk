# "grep" through a log file, and print a cause string to stdout
#
# Invoked from aports/regtest-html.sh

BEGIN {
  # we can add the bug number like #2338
  patterns["#2338"] = "\\@-D"  # variant after attempted glob fix
  # three backslashes is \\\-D
  patterns[50] = "\\\\\\-D"

  # This is a different pattern, so we use cause "##2338" to distinguish it
  # from "#2338".  It links to the same bug.
  patterns["##2338"] = "\\@(cd"  # variant after attempted glob fix
  # \\\(cd
  patterns[51] = "\\\\\\(cd"

  patterns[2] = "cannot create executable"

  patterns[3] = "cannot compile programs"

  patterns[4] = "test case names with"

  patterns[5] = "PHDR segment not covered"

  # OSH string
  patterns[6] = "error applying redirect:"

  # parsing error
  patterns[7] = "(((grep"

  # kea package: suspicious
  # oh this also fails with 124 though
  patterns[8] = "find a separator character in"

  # esh package: OSH string
  patterns[9] = "fatal: Undefined variable"

  # mawk: trap 0
  patterns[10] = "requires a signal or hook name"

  # pkgconf 
  patterns[11] = " with multiple files"

  # xz
  # musl libc error - with glibc, we get a parsing error
  patterns[12] = "Extended glob won"

  # sqlite
  patterns[13] = "No working C compiler"

  # sfic
  patterns[14] = "terminate called after throwing an instance of"

  # screen
  patterns[65] = "mkdir: invalid option --"
  patterns[15] = "mkdir: unrecognized option: /"  # changed 2025-08-04-rootbld

  # postfix
  patterns[16] = "Unexpected token after arithmetic expression"

  # make
  patterns[17] = "oils I/O error"

  # imap
  patterns[18] = "[ backticks in [ -c flag ] ]"

  # sqsh
  patterns[19] = "(test) Unexpected trailing word"

  found = 0
}
{ 
  for (i in patterns) {
    # search for the line
    if (index($0, patterns[i]) > 0) {
      print i
      found = 1

      # just print the first one, not every occurrence
      nextfile
    }
  }
}

END {
  if (!found) {
    print "unknown"  # no cause assigned
  }
}
