## compare_shells: bash zsh mksh
## oils_failures_allowed: 2

#### git-completion snippet

# copied directly from git completion - 2024-04

if false; then
  unset ${(M)${(k)parameters[@]}:#__gitcomp_builtin_*} 2>/dev/null
fi
echo status=$?

## STDOUT:
status=0
## END

#### asdf snippet

# copied directly from asdf - 2024-04

if false; then
  ASDF_DIR=${(%):-%x}
fi

## STDOUT:
## END
