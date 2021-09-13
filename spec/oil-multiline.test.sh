# This syntax is available with OSH too

#### ... with simple command
... echo  # comment
    hi  # comment
    there
    ;
## STDOUT:
hi there
## END

#### ... with pipeline
... { echo one; echo two; }
  | sort
  | wc -l
  ;
## STDOUT:
2
## END

#### ... with comment sub

# newlines mean the normal thing
echo $(echo one
       echo two)

... echo
    $(echo 3
      echo 4)  # is this right?
  | wc -l
  ;
## STDOUT:
2
## END

#### ... with && and [[
echo 1 && false || echo end

... echo one
 && [[ 0 -eq 0 ]]
 && echo two
 && false
 || echo end

## STDOUT:
one
two
## END

# Notes:
# - MakeParserForCommandSub() instantiates a new WordParser, so we can safetly
# change state in the top-level one only
# - BoolParser is called for [[ ]] and uses the same self.w_parser.  I think
# that's OK?

# So I think we can change state in WordParser.  (Also possible in
# CommandParser but meh).
#
# self.is_multiline = False
#
# When this is flag is on, then we
#
# Id.Op_Newline -> Id.WS_Space or Id.Ignored_LineCont
#  - and then that is NOT passed to the command parser?
#  - Or you can make it Id.Ignored_Newline
#
# BUT if you get 2 of them in a row without a comment, you can change it to:
# - Id.Op_Newline?
#
# Actually this is very simple rule and maybe can be done without much
# disturbance to the code.
#
# cursor_was_newline might need more state?





