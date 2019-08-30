#!/bin/bash

# Weird case from bash-help mailing list.
#
# "Evaluations of backticks in if statements".  It doesn't relate to if
# statements but to $?, since && and || behave the same way.

# POSIX has a special rule for this.  In OSH strict_argv is preferred so it
# becomes a moot point.  I think this is an artifact of the
# "stateful"/imperative nature of $? -- it can be "left over" from a prior
# command, and sometimes the prior argv is [].  OSH has a more "functional"
# implementation so it doesn't have this weirdness.

#### If empty command
if ''; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0

#### If subshell true
if `true`; then echo TRUE; else echo FALSE; fi
## stdout: TRUE
## status: 0

#### If subshell true WITH OUTPUT is different
if `sh -c 'echo X; true'`; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0

#### If subshell true WITH ARGUMENT
if `true` X; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0

#### If subshell false -- exit code is propagated in a weird way (strict_argv prevents)
if `false`; then echo TRUE; else echo FALSE; fi
## stdout: FALSE
## status: 0
