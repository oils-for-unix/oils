// data_lang.cc

#include "cpp/data_lang.h"

#include "data_lang/j8.h"
#include "data_lang/utf8_impls/bjoern_dfa.h"

// TODO: remove duplication
#define LOSSY_JSON (1 << 3)

namespace {

void WriteBString(BigStr* s, mylib::BufWriter* buf, int capacity) {
  uint8_t* in = reinterpret_cast<uint8_t*>(s->data_);
  uint8_t* in_end = reinterpret_cast<uint8_t*>(s->data_ + len(s));

  buf->WriteConst("b'");

  // Set up pointers after writing opening quote
  uint8_t* out = buf->LengthPointer();  // mutated
  uint8_t* out_end = buf->CapacityPointer();

  while (true) {
    J8EncodeChunk(&in, in_end, &out, out_end, true);  // Fill as much as we can
    buf->SetLengthFrom(out);

    if (in >= in_end) {
      break;
    }

    // Same growth policy as below
    capacity = capacity * 3 / 2;
    // printf("[2] new capacity %d\n", capacity);
    buf->EnsureMoreSpace(capacity);

    // Recompute pointers
    out = buf->LengthPointer();
    out_end = buf->CapacityPointer();
  }

  buf->WriteConst("'");
}

void WriteBashDollarString(BigStr* s, mylib::BufWriter* buf, int capacity) {
  uint8_t* in = reinterpret_cast<uint8_t*>(s->data_);
  uint8_t* in_end = reinterpret_cast<uint8_t*>(s->data_ + len(s));

  buf->WriteConst("$'");

  // Set up pointers after writing opening quote
  uint8_t* out = buf->LengthPointer();  // mutated
  uint8_t* out_end = buf->CapacityPointer();

  while (true) {
    BashDollarEncodeChunk(&in, in_end, &out,
                          out_end);  // Fill as much as we can
    buf->SetLengthFrom(out);

    if (in >= in_end) {
      break;
    }

    // Same growth policy as below
    capacity = capacity * 3 / 2;
    // printf("[2] new capacity %d\n", capacity);
    buf->EnsureMoreSpace(capacity);

    // Recompute pointers
    out = buf->LengthPointer();
    out_end = buf->CapacityPointer();
  }

  buf->WriteConst("'");
}

// Style is COPIED from pyj8::WriteString()
// Functionality is like j8_libc.c ShellEncodeString, that is:
//
// call BourneShellEncodeChunk()
// then either
//   WriteBString()
//   WriteBashDollarString()

void ShellEncodeString(BigStr* s, int ysh_fallback, mylib::BufWriter* buf) {
  uint8_t* in = reinterpret_cast<uint8_t*>(s->data_);
  uint8_t* in_end = reinterpret_cast<uint8_t*>(s->data_ + len(s));

  // Growth policy: Start at a fixed size max(N + 3 + 2, J8_MIN_CAPACITY)
  int capacity = len(s) + 3 + 2;     // 3 for quotes, 2 potential \" \n
  if (capacity < J8_MIN_CAPACITY) {  // account for J8_MAX_BYTES_PER_INPUT_BYTE
    capacity = J8_MIN_CAPACITY;
  }
  // printf("[1] capacity %d\n", capacity);

  buf->EnsureMoreSpace(capacity);

  int begin = buf->Length();  // maybe Truncate to this position
  buf->WriteConst("'");

  // Set up pointers after writing opening quote
  uint8_t* out = buf->LengthPointer();  // mutated
  uint8_t* out_end = buf->CapacityPointer();

  while (true) {
    // Fill in as much as we can
    int cannot_encode = BourneShellEncodeChunk(&in, in_end, &out, out_end);
    if (cannot_encode) {
      buf->Truncate(begin);
      if (ysh_fallback) {
        WriteBString(s, buf, capacity);  // fall back to b''
      } else {
        WriteBashDollarString(s, buf, capacity);  // fall back to $''
      }
      return;
    }
    buf->SetLengthFrom(out);

    // printf("[1] len %d\n", out_buf->len);

    if (in >= in_end) {
      break;
    }

    // Growth policy: every time through the loop, increase 1.5x
    //
    // The worst blowup is 6x, and 1.5 ** 5 > 6, so it will take 5 reallocs.
    // This seems like a reasonable tradeoff between over-allocating and too
    // many realloc().
    capacity = capacity * 3 / 2;
    // printf("[1] new capacity %d\n", capacity);
    buf->EnsureMoreSpace(capacity);

    // Recompute pointers
    out = buf->LengthPointer();  // mutated
    out_end = buf->CapacityPointer();
    // printf("[1] out %p out_end %p\n", out, out_end);
  }

  buf->WriteConst("'");
}

}  // namespace

namespace fastfunc {

bool CanOmitQuotes(BigStr* s) {
  return ::CanOmitQuotes(reinterpret_cast<unsigned char*>(s->data_), len(s));
}

BigStr* J8EncodeString(BigStr* s, int j8_fallback) {
  auto buf = Alloc<mylib::BufWriter>();
  int options = j8_fallback ? 0 : LOSSY_JSON;
  pyj8::WriteString(s, options, buf);
  return buf->getvalue();
}

BigStr* ShellEncodeString(BigStr* s, int ysh_fallback) {
  auto buf = Alloc<mylib::BufWriter>();
  ::ShellEncodeString(s, ysh_fallback, buf);
  return buf->getvalue();
}

}  // namespace fastfunc

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

void WriteString(BigStr* s, int options, mylib::BufWriter* buf) {
  bool j8_fallback = !(options & LOSSY_JSON);

  uint8_t* in = reinterpret_cast<uint8_t*>(s->data_);
  uint8_t* in_end = reinterpret_cast<uint8_t*>(s->data_ + len(s));

  // Growth policy: Start at a fixed size max(N + 3 + 2, J8_MIN_CAPACITY)
  int capacity = len(s) + 3 + 2;     // 3 for quotes, 2 potential \" \n
  if (capacity < J8_MIN_CAPACITY) {  // account for J8_MAX_BYTES_PER_INPUT_BYTE
    capacity = J8_MIN_CAPACITY;
  }
  // printf("[1] capacity %d\n", capacity);

  buf->EnsureMoreSpace(capacity);

  int begin = buf->Length();  // maybe Truncate to this position
  buf->WriteConst("\"");

  // Set up pointers after writing opening quote
  uint8_t* out = buf->LengthPointer();  // mutated
  uint8_t* out_end = buf->CapacityPointer();

  while (true) {
    // Fill in as much as we can
    int invalid_utf8 = J8EncodeChunk(&in, in_end, &out, out_end, false);
    if (invalid_utf8 && j8_fallback) {
      buf->Truncate(begin);
      WriteBString(s, buf, capacity);  // fall back to b''
      return;
    }
    buf->SetLengthFrom(out);

    // printf("[1] len %d\n", out_buf->len);

    if (in >= in_end) {
      break;
    }

    // Growth policy: every time through the loop, increase 1.5x
    //
    // The worst blowup is 6x, and 1.5 ** 5 > 6, so it will take 5 reallocs.
    // This seems like a reasonable tradeoff between over-allocating and too
    // many realloc().
    capacity = capacity * 3 / 2;
    // printf("[1] new capacity %d\n", capacity);
    buf->EnsureMoreSpace(capacity);

    // Recompute pointers
    out = buf->LengthPointer();  // mutated
    out_end = buf->CapacityPointer();
    // printf("[1] out %p out_end %p\n", out, out_end);
  }

  buf->WriteConst("\"");
}

}  // namespace pyj8

namespace j8 {

int HeapValueId(value_asdl::value_t* val) {
#ifndef OPTIMIZED
  // ASDL generates headers with HeapTag::Scanned, but HeapTag::FixedSize would
  // also be valid.
  ObjHeader* h = ObjHeader::FromObject(val);
  DCHECK(h->heap_tag == HeapTag::Scanned || h->heap_tag == HeapTag::FixedSize);
#endif

  return ObjectId(val);
}

}  // namespace j8
