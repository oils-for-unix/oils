#include "frontend_pyreadline.h"

#include <assert.h>

#include "_build/detected-cpp-config.h"

namespace py_readline {

void Readline::parse_and_bind(Str* s) {
  assert(0);  // not implemented
}

void Readline::add_history(Str* line) {
  assert(0);  // not implemented
}

void Readline::read_history_file(Str* path) {
  assert(0);  // not implemented
}

void Readline::write_history_file(Str* path) {
  assert(0);  // not implemented
}

void Readline::set_completer(ReadlineCompleterFunc completer) {
  assert(0);  // not implemented
}

void Readline::set_completer_delims(Str* delims) {
  assert(0);  // not implemented
}

void Readline::set_completion_display_matches_hook(
    ReadlineDisplayMatchesHookFunc hook) {
  assert(0);  // not implemented
}

Str* Readline::get_line_buffer() {
  assert(0);  // not implemented
}

int Readline::get_begidx() {
  assert(0);  // not implemented
}

int Readline::get_endidx() {
  assert(0);  // not implemented
}

void Readline::clear_history() {
  assert(0);  // not implemented
}

void Readline::remove_history_item(int pos) {
  assert(0);  // not implemented
}

Str* Readline::get_history_item(int pos) {
  assert(0);  // not implemented
}

int Readline::get_current_history_length() {
  assert(0);  // not implemented
}

void Readline::resize_terminal() {
  assert(0);  // not implemented
}

Readline* MaybeGetReadline() {
  // TODO: incorporate OIL_READLINE into the build config
#ifdef HAVE_READLINE
  return Alloc<Readline>();
#else
  return nullptr;
#endif
}

}  // namespace py_readline
