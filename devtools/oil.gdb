# GDB configuration or Oil
#
# Usage:
#   $ gdb
#   (gdb) source devtools/oil.gdb
#
# Or 'source' it from ~/.gdbinit

# for multiline structs
set print pretty on
# TODO: save history

# Our Python commands
source devtools/oil_gdb.py

define cls
    shell clear
end
document cls
Clear screen.
end
