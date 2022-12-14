// frontend_pyreadline.h

#ifndef FRONTEND_PYREADLINE_H
#define FRONTEND_PYREADLINE_H

#include "mycpp/runtime.h"

namespace py_readline {

typedef Str* (*ReadlineCompleterFunc)(Str*, int);
typedef void (*ReadlineDisplayMatchesHookFunc)(Str*, List<Str*>*, int);

class Readline : public Obj {
 public:
  Readline();
  void parse_and_bind(Str* s);
  void add_history(Str* line);
  void read_history_file(Str* path);
  void write_history_file(Str* path);
  void set_completer(ReadlineCompleterFunc completer);
  void set_completer_delims(Str* delims);
  void set_completion_display_matches_hook(
      ReadlineDisplayMatchesHookFunc hook = nullptr);
  Str* get_line_buffer();
  int get_begidx();
  int get_endidx();
  void clear_history();
  Str* get_history_item(int pos);
  void remove_history_item(int pos);
  int get_current_history_length();
  void resize_terminal();
};

Readline* MaybeGetReadline();

}  // namespace py_readline

#endif  // FRONTEND_PYREADLINE_H
