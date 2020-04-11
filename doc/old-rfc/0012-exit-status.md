Exit Status and Errexit
-----------------------

- bash: `inherit_exit` doesn't go far enough

- strict-errexit
  - does more than one thing


- pitfalls:
  - assignment builtin vs. bare assignment (different exit status)
  - errexit disabling is surprising
  - the issue bash's inherit_errexit solves -- doesn't  go far enough


- Dollar-At pattern: patterN: the Doissue $0

- Quoted-At Pattern
  - At-Splice pattern

  "$@" "${a[@]}"

  - @ARGV  or @@


