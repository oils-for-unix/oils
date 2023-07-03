# spec/ysh-case

## our_shell: ysh
## oils_failures_allowed: 0

#### Str->startsWith
= "abc"->startsWith("")
= "abc"->startsWith("a")
= "abc"->startsWith("z")
## status: 0
## STDOUT:
(Bool)   True
(Bool)   True
(Bool)   False
## END

#### Str->startsWith, no args
= "abc"->startsWith()
## status: 3

#### Str->startsWith, too many args
= "abc"->startsWith("extra", "arg")
## status: 3

#### Missing method (Str->doesNotExist())
= "abc"->doesNotExist()
## status: 3
