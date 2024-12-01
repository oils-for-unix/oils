## oils_failures_allowed: 4
## compare_shells: bash zsh

#### globstar is off -> ** is treated like *
case $SH in zsh) exit ;; esac

shopt -u globstar

mkdir -p c/subdir
touch {leaf.md,c/leaf.md,c/subdir/leaf.md}

echo **/*.* | sort
## STDOUT:
c/leaf.md
## END
## N-I zsh STDOUT:
## END

#### each occurrence of ** recurses through all depths
shopt -s globstar

mkdir -p c/subdir
touch {leaf.md,c/leaf.md,c/subdir/leaf.md}

echo **/*.* | tr ' ' '\n'
echo
echo **/**/*.* | tr ' ' '\n'
## STDOUT:
c/leaf.md
c/subdir/leaf.md
leaf.md

c/leaf.md
c/subdir/leaf.md
leaf.md
## END

## BUG zsh STDOUT:
c/leaf.md
c/subdir/leaf.md
leaf.md

c/leaf.md
c/leaf.md
c/subdir/leaf.md
c/subdir/leaf.md
c/subdir/leaf.md
leaf.md
## END

#### within braces, globstar works when there is a comma
shopt -s globstar

mkdir -p c/subdir
touch c/subdir/leaf.md

echo {**/*.*,} | sort -u | sed 's/[[:space:]]*$//'
## STDOUT:
c/subdir/leaf.md
## END

#### ** behaves like * if adjacent to anything other than /
shopt -s globstar

mkdir directory
touch leaf.md
touch directory/leaf.md

echo **/*.* | sort -u
echo directory/**/*.md | sort -u
echo d**/*.md | sort -u
echo **y/*.md | sort -u
echo d**y/*.md | sort -u
## STDOUT:
directory/leaf.md leaf.md
directory/leaf.md
directory/leaf.md
directory/leaf.md
directory/leaf.md
## END

#### in zsh, ***/ follows symlinked directories, while **/ does not
case $SH in bash) exit ;; esac

mkdir directory-1
mkdir directory-2
touch directory-2/leaf-2.md
ln -s -T ../directory-2 directory-1/symlink

echo **/*.* | sort -u
echo ***/*.* | sort -u
## STDOUT:
directory-2/leaf-2.md
directory-1/symlink/leaf-2.md directory-2/leaf-2.md
## END
## N-I bash STDOUT:
## END
