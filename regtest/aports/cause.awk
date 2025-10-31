# "grep" through a log file, and print a cause string to stdout
#
# Invoked from aports/regtest-html.sh

BEGIN {
  patterns["makedepends"] = "ERROR: No such package: .makedepends"
  # e.g. xkeyboard-config flakiness
  patterns["fetch-failed"] = ": fetch failed"

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

  # abuild, ifupdown-ng, ...
  patterns["#2416"] = "test case names with"
  # jemalloc appears to be the same root cause
  patterns["##2416"] = "jemalloc/internal/private_namespace.h: No such file or directory"

  # e2fsprogs - not sure how to narrow this down more?
  patterns["#2413"] = "382 tests succeeded	1 tests failed"

  patterns[5] = "PHDR segment not covered"

  # OSH string
  patterns[6] = "error applying redirect:"

  # parsing error
  patterns["#2337"] = "(((grep"
  #patterns["##2337"] = "Parser expected Id.Arith_RParen, got Id.Word_Compound"

  # postfix
  # gzip
  patterns["##2337"] = "Unexpected token after arithmetic expression"

  # kea package: suspicious
  # oh this also fails with 124 though
  patterns[8] = "find a separator character in"

  # esh package: OSH string
  # I am not sure these are real bugs: it might be that esh expects and exact
  # code string?
  patterns[9] = "fatal: Undefined variable"

  # mawk, openvpn: trap 0
  patterns["#2339"] = "requires a signal or hook name"

  # pkgconf 
  patterns[11] = " with multiple files"

  # xz
  # musl libc error - with glibc, we get a parsing error
  patterns["#2336"] = "Extended glob won"

  # sqlite
  patterns[13] = "No working C compiler"

  # sfic
  patterns["#2411"] = "terminate called after throwing an instance of"

  # screen
  patterns["#2364"] = "mkdir: unrecognized option: /"  # changed 2025-08-04-rootbld
  patterns["##2364"] = "mkdir: invalid option --"

  # make
  patterns["#2335"] = "oils I/O error"
  # patch is the same ulimit bug, but the "invalid argument" EINVAL string
  # occurs in test-suite.log
  patterns["##2335"] = "patch: check failed"

  # sqsh
  patterns["#2409"] = "(test) Unexpected trailing word"

  # xz
  # note: with glibc, a different string will appear
  patterns["#2336"] = "Extended glob won't work without FNM_EXTMATCH support in libc"

  #
  # BUGS that only occur with OSH as BUSYBOX ASH
  #

  # heimdal, perl
  patterns["#2424"] = "Found uncompressed man pages:"

  # nginx
  patterns["#2425"] = "'cd' got too many arguments"

  #
  # BUGS that only occur with OSH as BASH
  #

  # chrony
  patterns["#2426"] = "In expressions, remove $ and use `OPTIND`"

  # shorewall - BAD version detection - fixed
  #patterns["#2427"] = "ERROR: This program requires Bash 4.0 or later"

  # gdbm
  patterns["#2429"] = "ERROR: gdbm: check failed"

  # shorewall
  patterns["#2438"] = "Assoc array keys must be strings"

  # zfs
  patterns["#2441"] = "Token starting at column"

  # 2025-10-26: demo for updating cause.awk, already fixed
  patterns["#2477"] = "printf expected an integer, got"

  # mdev-conf
  patterns["#2500"] = "readlink disk/by-label/EFI"

  # zeitgeist
  patterns["#2528"] = "Unexpected argument to \'exit\'"

  # dircproxy
  patterns["#2535"] = "fatal: Pat Sub op expected Str, BashArray, or BashAssoc, got Int"

  # jq
  patterns["#2540"] = "FAIL: tests/shtest"

  # libidn
  patterns["#2523"] = "ERROR: libidn2: check failed"

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
