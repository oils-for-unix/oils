## compare_shells: bash

#### cdable_vars: resolve variable to path
shopt -s cdable_vars
export TARGET_DIR='/tmp'
cd TARGET_DIR
pwd
## status: 0
## STDOUT:
/tmp
/tmp
## END

#### cdable_vars: fails when shopt is off
shopt -u cdable_vars
TARGET_DIR='/tmp'
cd TARGET_DIR
## status: 1

#### cdable_vars: Fails if variable points to a file, not a directory
shopt -s cdable_vars
touch my_file
VAR_NAME='my_file'
cd VAR_NAME
## status: 1
