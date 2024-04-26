## compare_shells: bash zsh mksh

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

#### zsh var sub is rejected at runtime

echo z ${(m)foo} z
echo status=$?

## status: 1
## STDOUT:
## END

## OK zsh status: 0
## OK zsh STDOUT:
z z
status=0
## END

## OK bash status: 0
## OK bash STDOUT:
status=1
## END
