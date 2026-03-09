## compare_shells: bash

#### cdable_vars: resolve variable to path
shopt -s cdable_vars
export TARGET_DIR='/tmp'
cd TARGET_DIR
pwd
## status: 0
## STDOUT:
/tmp
## END
## OK bash STDOUT:
/tmp
/tmp
## END

#### cdable_vars: fails when shopt is off
shopt -u cdable_vars
TARGET_DIR='/tmp'
cd TARGET_DIR
## status: 1

#### cdable_vars: normal path still works when cdable_vars is set
shopt -s cdable_vars
cd /tmp
pwd
## status: 0
## STDOUT:
/tmp
## END

#### cdable_vars: path takes priority over variable with same name
shopt -s cdable_vars
mkdir -p /tmp/testdir
cd /tmp/testdir
pwd
## status: 0
## STDOUT:
/tmp/testdir
## END

#### cdable_vars: fails if variable points to a file not a directory
shopt -s cdable_vars
touch /tmp/my_file
VAR_NAME='my_file'
cd VAR_NAME
## status: 1

#### cdable_vars: fails if variable is unset
shopt -s cdable_vars
unset TARGET_DIR
cd TARGET_DIR
## status: 1

#### cdable_vars: array variable resolves to first element
shopt -s cdable_vars
TARGET_DIR=('/tmp' '/home')
cd TARGET_DIR
## status: 1
## BUG bash status: 0
