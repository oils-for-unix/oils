#### cdable_vars: resolve variable to path
shopt -s cdable_vars
TARGET_DIR='/tmp'
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
