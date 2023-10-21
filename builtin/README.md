builtin/
=======

Procs and funcs that are compiled into the Oils binary.

Naming convention that allows us to compare OSH code size versus bash:

    builtin/
      func_hay.py  # functions only appear in YSH

      io_osh.py  # read builtin is in OSH, with YSH enhancements
      io_ysh.py  # write builtin is only in YSH

      pure_osh.py  # set, shopt
      pure_ysh.py  # append

      trap_osh.py  # trap
      json_ysh.py  # json

