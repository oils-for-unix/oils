Yaks Syntax
===========

## CST-Like IR

    (class ParseHay vm._Callable  # we have limited infix . for readability
                                  # WASM also has this?
      (var fd_state process.FdState)
      (var parse_ctx parse_lib.ParseContext)
 
      (func _init [this.fd_state, this.parse_ctx, this.errfmt]
      )
 
      (func _Call [path Str] value_t
        (var call_loc loc.Missing)
 
        # https://stackoverflow.com/questions/16493079/how-to-implement-a-try-catch-block-in-scheme
 
        (try  # extra level of indent is annoying
          (var f (this.fd_state.Open path))
          (except [IOError_OSError] [e] 
            (var msg (posix.sterror e.errno))
            (throw error.Expr (fmt "Couldn't open "%r: %s" path msg) call_loc))
          (except ...
            )
        )
      )
    )
 
    (class ctx_Try []
      (var mutable_opts MutableOpts)
 
      (func _init [this.fd_state, this.parse_ctx, this.errfmt]
        (mutableOpts.Push option_i.errexit True)
      )
      (func _destroy []
        (this.mutable_ops.Pop option_i.errexit)
      )
    )
 
OK this is actually not bad.  And it saves us from reusing YSH syntax.  Hm.
think we just need the infix dot sugar in the reader?

Note that the bootstrap compiler won't have `class try with`.

- It will only have `func data enum`, `global var setvar`, `for while`, `if switch`.
  - Globals are always constants, and incur no startup time.

## Abandoned YSH-like syntax -- too much work

Example of better syntax which we already support:

    func f(a List[Int], b Dict[Str, Int]) {
      case (node->tag()) {
        (command_e.Simple) {
        }
        (command_e.ShAssignment) {
        }
      }
 
      # We would need to add something like this?
      with (dev.ctx_Tracer(this.tracer, 'source', cmd_val.argv)) {
        var source_argv = arg_r.Rest()  # C++ needs type inference here?
      }
      return (x)
    }
 
Example of class support

- static stuff which I added in ysh/grammar.pgen2:
- virtual override abstract - this isn't horrible

    class ParseHay : vm._Callable {
      var fd_state: process.FdState
      var parse_ctx: parse_lib.ParseContext
      var errfmt: ui.ErrorFormatter
 
      # auto-assign members, infer types
      func init(this.fd_state, this.parse_ctx, this.errfmt) {
      }
  
      func _Call(path Str) -> value_t {
        var call_loc = loc.Missing
        try {
          var f = this.fd_state.Open(path)
        } except (IOError, OSError) as e {  # can paper over IOError
          var msg = posix.strerror(e.errno)
          throw error.Expr("Couldn't open %r: %s" % (path, msg), call_loc)
        }
      }
    }

    class ctx_Try {
      var mutable_opts: MutableOpts
 
      # would we have 'fn' that gets rid of :: ?  Perhaps
      func _init(this.mutable_opts) {
        :: mutable_opts.Push(option_i.errexit, true)
      }
 
      func _destroy() {
        this.mutable_opts.Pop(option_i.errexit)
      }
    }
 
Problem: this would break INTERPRETER flow, unless you generate Python!  which
is possible, though possibly ugly.
 
This is another reason not to use it.

