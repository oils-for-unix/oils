# GDB configuration or Oil
#
# Usage:
#   $ gdb
#   (gdb) source devtools/oil.gdb
#
# Or 'source' it from ~/.gdbinit


# Our Python commands
source devtools/oil_gdb.py

define cls
    shell clear
end
document cls
Clear screen.
end
