// data_lang.cc

#include "cpp/data_lang.h"

#include "data_lang/j8.h"
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

const int LOSSY_JSON = 1 << 3;  // TODO: remove duplication

void WriteString(BigStr* s, int options, mylib::BufWriter* buf) {
  bool j8_escape = !(options & LOSSY_JSON);

  uint8_t* input = reinterpret_cast<unsigned char*>(s->data_);

  // We also need RemainingBytes()
  uint8_t* output = buf->CurrentPos();

  uint8_t** in = &input;
  uint8_t** out = &output;

  int invalid_utf8 = 0;
  //invalid_utf8 = EncodeRuneOrByte(in, out, j8_escape);

  // Growth algorithm
  //
  // data_lang/j8.py looks like this:
  // for k, v in iteritems(val.d):
  //     if i != 0:
  //         self.buf.write(',')
  //         self.buf.write(maybe_newline)

  //     self.buf.write(item_indent)
  //     pyj8.WriteString(s, self.options, self.buf)

  //     self.buf.write(':')
  //     self.buf.write(maybe_space)

  //     self.Print(v, level + 1)
  //
  // So there are a bunch of small constant and variable strings.
  //
  // write() does buf->reserve_capacity(len_ + n)

  // I think we need buf->ReserveMore(5)  // 5 more bytes
  //
  // and then query RemainingBytes()
  //
}

}  // namespace pyj8
