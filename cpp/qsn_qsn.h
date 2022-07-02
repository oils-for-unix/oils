// qsn_qsn.h

#ifndef QSN_QSN_H
#define QSN_QSN_H

#ifdef LEAKY_BINDINGS
#include "mycpp/mylib_leaky.h"
using gc_heap::StackRoots;  // no-op
using mylib::BlankStr;
using mylib::CopyStr;
using mylib::OverAllocatedStr;
#else
#include "mycpp/gc_heap.h"
using gc_heap::BlankStr;
using gc_heap::CopyStr;
using gc_heap::OverAllocatedStr;
using gc_heap::StackRoots;
using gc_heap::Str;
#endif

namespace qsn {

inline bool IsUnprintableLow(Str* ch) {
  assert(len(ch) == 1);
  return ch->data_[0] < ' ';
}

inline bool IsUnprintableHigh(Str* ch) {
  assert(len(ch) == 1);
  return ch->data_[0] >= 0x7f;
}

inline bool IsPlainChar(Str* ch) {
  assert(len(ch) == 1);
  uint8_t c = ch->data_[0];
  switch (c) {
  case '.':
  case '-':
  case '_':
    return true;
  }
  return ('a' <= c && c <= 'z') || ('A' <= c && c <= 'Z') ||
         ('0' <= c && c <= '9');
}

inline Str* XEscape(Str* ch) {
  assert(len(ch) == 1);
  StackRoots _roots({&ch});
  Str* result = BlankStr(4);
  sprintf(result->data(), "\\x%02x", ch->data_[0] & 0xff);
  return result;
}

inline Str* UEscape(int codepoint) {
  // maximum length:
  // 3 for \u{
  // 6 for codepoint
  // 1 for }
  Str* result = OverAllocatedStr(10);
  int n = sprintf(result->data(), "\\u{%x}", codepoint);
  result->SetObjLenFromStrLen(n);  // truncate to what we wrote
  return result;
}

}  // namespace qsn

#endif  // QSN_QSN_H
