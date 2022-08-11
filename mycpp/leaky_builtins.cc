#ifdef OLDSTL_BINDINGS
  #include "mycpp/oldstl_containers.h"
#else
  #include "mycpp/gc_builtins.h"
  #include "mycpp/gc_containers.h"
#endif

#include <ctype.h>  // isspace()

// Translation of Python's print().
void print(Str* s) {
  fputs(s->data(), stdout);
  fputs("\n", stdout);
}

// Like print(..., file=sys.stderr), but Python code explicitly calls it.
void println_stderr(Str* s) {
  fputs(s->data(), stderr);
  fputs("\n", stderr);
}

Str* str_repeat(Str* s, int times) {
  // Python allows -1 too, and Oil used that
  if (times <= 0) {
    return kEmptyString;
  }
  int len_ = len(s);
  int new_len = len_ * times;
  char* data = static_cast<char*>(malloc(new_len + 1));

  char* dest = data;
  for (int i = 0; i < times; i++) {
    memcpy(dest, s->data_, len_);
    dest += len_;
  }
  data[new_len] = '\0';
  return CopyBufferIntoNewStr(data, new_len);
}

// Helper for str_to_int() that doesn't use exceptions.
// Like atoi(), but with better error checking.
bool _str_to_int(Str* s, int* result, int base) {
  int s_len = len(s);
  if (s_len == 0) {
    return false;  // special case for empty string
  }

  char* p;  // mutated by strtol

  long v = strtol(s->data(), &p, base);
  switch (v) {
  case LONG_MIN:
    // log("underflow");
    return false;
  case LONG_MAX:
    // log("overflow");
    return false;
  }

  *result = v;

  // Return true if it consumed ALL characters.
  const char* end = s->data_ + s_len;

  // log("start %p   p %p   end %p", s->data_, p, end);
  if (p == end) {
    return true;
  }

  // Trailing space is OK!
  while (p < end) {
    if (!isspace(*p)) {
      return false;
    }
    p++;
  }
  return true;
}

// for os_path.join()
// NOTE(Jesse): Perfect candidate for bounded_buffer
Str* str_concat3(Str* a, Str* b, Str* c) {
  int a_len = len(a);
  int b_len = len(b);
  int c_len = len(c);

  int new_len = a_len + b_len + c_len;
  char* buf = static_cast<char*>(malloc(new_len));
  char* pos = buf;

  memcpy(pos, a->data_, a_len);
  pos += a_len;

  memcpy(pos, b->data_, b_len);
  pos += b_len;

  memcpy(pos, c->data_, c_len);

  assert(pos + c_len == buf + new_len);

  return CopyBufferIntoNewStr(buf, new_len);
}

Str* str_concat(Str* a, Str* b) {
  int a_len = len(a);
  int b_len = len(b);
  int new_len = a_len + b_len;
  char* buf = static_cast<char*>(malloc(new_len + 1));

  memcpy(buf, a->data_, a_len);
  memcpy(buf + a_len, b->data_, b_len);
  buf[new_len] = '\0';

  return CopyBufferIntoNewStr(buf, new_len);
}

int to_int(Str* s, int base) {
  int i;
  if (_str_to_int(s, &i, base)) {
    return i;
  } else {
    throw new ValueError();
  }
}

int to_int(Str* s) {
  int i;
  if (_str_to_int(s, &i, 10)) {
    return i;
  } else {
    throw new ValueError();
  }
}

