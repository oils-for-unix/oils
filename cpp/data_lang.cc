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
  uint8_t* input_end = reinterpret_cast<unsigned char*>(s->data_ + len(s));

  // unsigned char* out = buf->str_->data_;         // mutated
  // unsigned char* orig_out = out;

  // TODO: have to rewind to this position
  buf->WriteConst("\"");

  uint8_t* output = buf->CurrentPos();

  // I think we do an OPTIMISTIC
  // EnsureMoreSpace(input_length)
  // and then we loop while we have less than 6 bytes left
  // TODO: maybe use the std::string or std::vector API to test it?

  // Problem: we can't implement this with std::string!
  // because we're breaking the invariant of the data structure
  // string::append() takes a char, and mutates its length

  // we could maintain a fixed size buffer of 128 or something, and copy it?

#if 0
  int invalid_utf8 = 0;
  while (input < input_end) {
    buf->EnsureMoreSpace(J8_MAX_BYTES_PER_INPUT_BYTE);  // 6 bytes at most
    // PROBLEM: every time you call this, the output can be MOVED!
    // So do you have to return a boolean then?

    // TRICKY / UNSAFE: This updates our local pointer 'output', as well as
    // memory owned by the BufWriter.
    invalid_utf8 = EncodeRuneOrByte(&input, &output, j8_escape);
    if (invalid_utf8) {
      // Rewind?
      buf.WriteConst("b'");
      while (input < input_end) {
        // some of this could be avoided
        buf->EnsureMoreSpace(J8_MAX_BYTES_PER_INPUT_BYTE);  // 6 bytes at most
        EncodeRuneOrByte(&input, &output, j8_escape);
      }
      // TODO: update BufWriter

      buf.WriteConst("'");
    }
    // TODO: update BufWriter
  }
#endif

  buf->WriteConst("\"");

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
