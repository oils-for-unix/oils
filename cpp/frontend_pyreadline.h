// frontend_pyreadline.h

#ifndef FRONTEND_PYREADLINE_H
#define FRONTEND_PYREADLINE_H

#include "mycpp/runtime.h"

// hacky forward decl
namespace completion {
class ReadlineCallback;
Str* ExecuteReadlineCallback(ReadlineCallback*, Str*, int);
}  // namespace completion

// hacky forward decl
namespace comp_ui {
class _IDisplay;
void ExecutePrintCandidates(_IDisplay*, Str*, List<Str*>*, int);
}  // namespace comp_ui

namespace py_readline {

class Readline {
 public:
  Readline();
  void parse_and_bind(Str* s);
  void add_history(Str* line);
  void read_history_file(Str* path);
  void write_history_file(Str* path);
  void set_completer(completion::ReadlineCallback* completer);
  void set_completer_delims(Str* delims);
  void set_completion_display_matches_hook(
      comp_ui::_IDisplay* display = nullptr);
  Str* get_line_buffer();
  int get_begidx();
  int get_endidx();
  void clear_history();
  Str* get_history_item(int pos);
  void remove_history_item(int pos);
  int get_current_history_length();
  void resize_terminal();

  static constexpr uint32_t field_mask() {
    return maskbit(offsetof(Readline, completer_delims_)) |
           maskbit(offsetof(Readline, completer_)) |
           maskbit(offsetof(Readline, display_));
  }

  static constexpr ObjHeader obj_header() {
    return ObjHeader::ClassFixed(field_mask(), sizeof(Readline));
  }

  int begidx_;
  int endidx_;
  Str* completer_delims_;
  completion::ReadlineCallback* completer_;
  comp_ui::_IDisplay* display_;

  // readline will set this to NULL when EOF is received, else this will point
  // to a line of input.
  char* latest_line_;

  // readline will set this flag when either:
  //   - it receives EOF
  //   - it has a complete line of input (it has seen "\n")
  bool ready_;
};

Readline* MaybeGetReadline();

Str* readline(Str* prompt);

}  // namespace py_readline

#endif  // FRONTEND_PYREADLINE_H
