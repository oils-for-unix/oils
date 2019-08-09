Oil String Literals
-------------------

Problem: Do we want C strings or raw strings?


Command Mode and Expression Mode strings look the same:

    var a = 'ls -l'            
    var b = "hello $world"
    echo 'ls -l' "hello $world"

We have a problem when there are backslashes:

    var tab = '\t'   # ambiguous, syntax error!!!

Solution: Any string with a backslash needs either an r or c prefix

    var two_chars = r'\t'  # shell "raw" strings: 2 characters
    var tab = c'\t'  # 2 character

Ditto for double-quoted:

   var two_chars = r"\t"  # shell "raw" strings: 2 characters
   var tab = c"\t"        # 2 character


### Implementation Details

- c'' and r'' have their own lexer modes
- '' is lexed like a C string.  If there are any escape codes, then an error is
  raised.  It needs an explicit `c` prefix.

