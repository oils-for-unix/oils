// leaky_core_error.cc

#include "cpp/leaky_core_error.h"

namespace error {

Usage::Usage(Str* msg, int span_id)
    : Obj(Tag::FixedSize, maskof_Usage(), sizeof(Usage)),
      msg(msg),
      span_id(span_id) {
}

Usage::Usage(Str* msg)
    : Obj(Tag::FixedSize, maskof_Usage(), sizeof(Usage)),
      msg(msg),
      span_id(runtime::NO_SPID) {
}

_ErrorWithLocation::_ErrorWithLocation(Str* user_str, int span_id)
    : Obj(Tag::FixedSize, maskof__ErrorWithLocation(),
          sizeof(_ErrorWithLocation)),
      status(1),
      user_str_(user_str),
      span_id(span_id),
      token(nullptr),
      part(nullptr),
      word(nullptr) {
}
_ErrorWithLocation::_ErrorWithLocation(Str* user_str, Token* token)
    : Obj(Tag::FixedSize, maskof__ErrorWithLocation(),
          sizeof(_ErrorWithLocation)),
      status(1),
      user_str_(user_str),
      span_id(runtime::NO_SPID),
      token(token),
      part(nullptr),
      word(nullptr) {
}
_ErrorWithLocation::_ErrorWithLocation(Str* user_str, word_part_t* part)
    : Obj(Tag::FixedSize, maskof__ErrorWithLocation(),
          sizeof(_ErrorWithLocation)),
      status(1),
      user_str_(user_str),
      span_id(runtime::NO_SPID),
      token(nullptr),
      part(part),
      word(nullptr) {
}
_ErrorWithLocation::_ErrorWithLocation(Str* user_str, word_t* word)
    : Obj(Tag::FixedSize, maskof__ErrorWithLocation(),
          sizeof(_ErrorWithLocation)),
      status(1),
      user_str_(user_str),
      span_id(runtime::NO_SPID),
      token(nullptr),
      part(nullptr),
      word(word) {
}
_ErrorWithLocation::_ErrorWithLocation(int status, Str* user_str, int span_id,
                                       bool show_code)
    : Obj(Tag::FixedSize, maskof__ErrorWithLocation(),
          sizeof(_ErrorWithLocation)),
      status(status),
      user_str_(user_str),
      span_id(span_id),
      token(nullptr),
      part(nullptr),
      word(nullptr),
      show_code(show_code) {
}

}  // namespace error
