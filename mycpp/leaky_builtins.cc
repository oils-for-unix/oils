#include <ctype.h>  // isspace()

#include "mycpp/runtime.h"

mylib::BufWriter gBuf;

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

Str* str(int i) {
  Str* s = OverAllocatedStr(kIntBufSize);
  int length = snprintf(s->data(), kIntBufSize, "%d", i);
  s->SetObjLenFromStrLen(length);
  return s;
}

Str* repr(Str* s) {
  mylib::BufWriter f;
  f.format_r(s);
  return f.getvalue();
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

int to_int(Str* s, int base) {
  int i;
  if (_str_to_int(s, &i, base)) {
    return i;
  } else {
    throw Alloc<ValueError>();
  }
}

int to_int(Str* s) {
  int i;
  if (_str_to_int(s, &i, 10)) {
    return i;
  } else {
    throw Alloc<ValueError>();
  }
}

Str* chr(int i) {
  // NOTE: i should be less than 256, in which we could return an object from
  // GLOBAL_STR() pool, like StrIter
  auto result = AllocStr(1);
  result->data_[0] = i;
  return result;
}

int ord(Str* s) {
  assert(len(s) == 1);
  // signed to unsigned conversion, so we don't get values like -127
  uint8_t c = static_cast<uint8_t>(s->data_[0]);
  return c;
}

bool to_bool(Str* s) {
  return len(s) != 0;
}

double to_float(Str* s) {
  double result = atof(s->data_);
  return result;
}

// e.g. ('a' in 'abc')
bool str_contains(Str* haystack, Str* needle) {
  // Common case
  if (len(needle) == 1) {
    return memchr(haystack->data_, needle->data_[0], len(haystack));
  }

  if (len(needle) > len(haystack)) {
    return false;
  }

  // General case. TODO: We could use a smarter substring algorithm.

  const char* end = haystack->data_ + len(haystack);
  const char* last_possible = end - len(needle);
  const char* p = haystack->data_;

  while (p <= last_possible) {
    if (memcmp(p, needle->data_, len(needle)) == 0) {
      return true;
    }
    p++;
  }
  return false;
}

Str* str_repeat(Str* s, int times) {
  // Python allows -1 too, and Oil used that
  if (times <= 0) {
    return kEmptyString;
  }
  int len_ = len(s);
  int new_len = len_ * times;
  Str* result = AllocStr(new_len);

  char* dest = result->data_;
  for (int i = 0; i < times; i++) {
    memcpy(dest, s->data_, len_);
    dest += len_;
  }
  return result;
}

// for os_path.join()
// NOTE(Jesse): Perfect candidate for bounded_buffer
Str* str_concat3(Str* a, Str* b, Str* c) {
  int a_len = len(a);
  int b_len = len(b);
  int c_len = len(c);

  int new_len = a_len + b_len + c_len;
  Str* result = AllocStr(new_len);
  char* pos = result->data_;

  memcpy(pos, a->data_, a_len);
  pos += a_len;

  memcpy(pos, b->data_, b_len);
  pos += b_len;

  memcpy(pos, c->data_, c_len);

  assert(pos + c_len == result->data_ + new_len);

  return result;
}

Str* str_concat(Str* a, Str* b) {
  int a_len = len(a);
  int b_len = len(b);
  int new_len = a_len + b_len;
  Str* result = AllocStr(new_len);
  char* buf = result->data_;

  memcpy(buf, a->data_, a_len);
  memcpy(buf + a_len, b->data_, b_len);

  return result;
}

//
// Comparators
//

bool str_equals(Str* left, Str* right) {
  // Fast path for identical strings.  String deduplication during GC could
  // make this more likely.  String interning could guarantee it, allowing us
  // to remove memcmp().
  if (left == right) {
    return true;
  }

  // obj_len_ equal implies string lengths are equal

  if (left->obj_len_ == right->obj_len_) {
    assert(len(left) == len(right));
    return memcmp(left->data_, right->data_, len(left)) == 0;
  }

  return false;
}

bool maybe_str_equals(Str* left, Str* right) {
  if (left && right) {
    return str_equals(left, right);
  }

  if (!left && !right) {
    return true;  // None == None
  }

  return false;  // one is None and one is a Str*
}

// TODO(Jesse): Make an inline version of this
bool are_equal(Str* left, Str* right) {
  return str_equals(left, right);
}

// TODO(Jesse): Make an inline version of this
bool are_equal(int left, int right) {
  return left == right;
}

// TODO(Jesse): Make an inline version of this
bool keys_equal(int left, int right) {
  return left == right;
}

// TODO(Jesse): Make an inline version of this
bool keys_equal(Str* left, Str* right) {
  return are_equal(left, right);
}

bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2) {
  bool result = are_equal(t1->at0(), t2->at0());
  result = result && (t1->at1() == t2->at1());
  return result;
}

bool str_equals0(const char* c_string, Str* s) {
  int n = strlen(c_string);
  if (len(s) == n) {
    return memcmp(s->data_, c_string, n) == 0;
  } else {
    return false;
  }
}
