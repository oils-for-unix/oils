// data_lang.cc

#include "cpp/data_lang.h"

#include "data_lang/utf8_impls/bjoern_dfa.h"

namespace pyj8 {

bool PartIsUtf8(BigStr* s, int start, int end) {
  uint32_t codepoint;
  uint32_t state = UTF8_ACCEPT;

  for (int i = start; i < end; ++i) {
    // This var or a static_cast<> is necessary.  Should really change BigStr*
    // to use unsigned type
    uint8_t c = s->data_[i];
    decode(&state, &codepoint, c);
    if (state == UTF8_REJECT) {
      return false;
    }
  }

  return state == UTF8_ACCEPT;
}

}  // namespace pyj8
