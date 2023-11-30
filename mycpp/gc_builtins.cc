#include <ctype.h>  // isspace()
#include <errno.h>  // errno
#include <float.h>  // DBL_MIN, DBL_MAX
#include <math.h>   // INFINITY
#include <stdio.h>  // required for readline/readline.h (man readline)

#include "_build/detected-cpp-config.h"
#include "mycpp/runtime.h"
#ifdef HAVE_READLINE
  #include "cpp/frontend_pyreadline.h"
#endif

// Translation of Python's print().
void print(BigStr* s) {
  fputs(s->data_, stdout);  // print until first NUL
  fputc('\n', stdout);
}

BigStr* str(int i) {
  BigStr* s = OverAllocatedStr(kIntBufSize);
  int length = snprintf(s->data(), kIntBufSize, "%d", i);
  s->MaybeShrink(length);
  return s;
}

// TODO:
// - This could use a fancy exact algorithm, not libc
// - Does libc depend on locale?
BigStr* str(double d) {
  char buf[64];  // overestimate, but we use snprintf() to be safe

  // Problem:
  // %f prints 3.0000000 and 3.500000
  // %g prints 3 and 3.5
  //
  // We want literal syntax to indicate float, so add '.'

  int n = sizeof(buf) - 2;  // in case we add '.0'

  // %.9g digits for string that can be converted back to the same FLOAT
  // (not double)
  // https://stackoverflow.com/a/21162120
  // https://en.cppreference.com/w/cpp/types/numeric_limits/max_digits10
  int length = snprintf(buf, n, "%.9g", d);

  // %a is a hexfloat form, could use that somewhere
  // int length = snprintf(buf, n, "%a", d);

  if (strchr(buf, 'i')) {  // inf or -inf
    return StrFromC(buf);
  }

  if (!strchr(buf, '.')) {  // 12345 -> 12345.0
    buf[length] = '.';
    buf[length + 1] = '0';
    buf[length + 2] = '\0';
  }

  return StrFromC(buf);
}

// Do we need this API?  Or is mylib.InternedStr(BigStr* s, int start, int end)
// better for getting values out of Token.line without allocating?
//
// e.g. mylib.InternedStr(tok.line, tok.start, tok.start+1)
//
// Also for SmallStr, we don't care about interning.  Only for HeapStr.

BigStr* intern(BigStr* s) {
  // TODO: put in table gHeap.interned_
  return s;
}

// Print quoted string.  TODO: use C-style strings (YSTR)
BigStr* repr(BigStr* s) {
  // Worst case: \0 becomes 4 bytes as '\\x00', and then two quote bytes.
  int n = len(s);
  int upper_bound = n * 4 + 2;

  BigStr* result = OverAllocatedStr(upper_bound);

  // Single quote by default.
  char quote = '\'';
  if (memchr(s->data_, '\'', n) && !memchr(s->data_, '"', n)) {
    quote = '"';
  }
  char* p = result->data_;

  // From PyString_Repr()
  *p++ = quote;
  for (int i = 0; i < n; ++i) {
    char c = s->data_[i];
    if (c == quote || c == '\\') {
      *p++ = '\\';
      *p++ = c;
    } else if (c == '\t') {
      *p++ = '\\';
      *p++ = 't';
    } else if (c == '\n') {
      *p++ = '\\';
      *p++ = 'n';
    } else if (c == '\r') {
      *p++ = '\\';
      *p++ = 'r';
    } else if (isprint(c)) {
      *p++ = c;
    } else {  // Unprintable is \xff
      sprintf(p, "\\x%02x", c & 0xff);
      p += 4;
    }
  }
  *p++ = quote;
  *p = '\0';

  int length = p - result->data_;
  result->MaybeShrink(length);
  return result;
}

// Helper for str_to_int() that doesn't use exceptions.
bool StringToInteger(const char* s, int length, int base, int* result) {
  if (length == 0) {
    return false;  // empty string isn't a valid integer
  }

  // Empirically this is 4 4 8 on 32-bit and 4 8 8 on 64-bit
  // We want the bigger numbers
#if 0
  log("sizeof(int) = %d", sizeof(int));
  log("sizeof(long) = %ld", sizeof(long));
  log("sizeof(long long) = %ld", sizeof(long long));
  log("");
  log("LONG_MAX = %ld", LONG_MAX);
  log("LLONG_MAX = %lld", LLONG_MAX);
#endif

  char* pos;  // mutated by strtol

  long v = strtol(s, &pos, base);

  // The problem with long long is that mycpp deals with C++ int
  // long long v = strtoll(s, &pos, base);

  // log("v = %ld", v);

  switch (v) {
  case LONG_MIN:
    return false;  // underflow
  case LONG_MAX:
    return false;  // overflow
  }

  const char* end = s + length;
  if (pos == end) {
    *result = v;
    return true;  // strtol() consumed ALL characters.
  }

  while (pos < end) {
    if (!isspace(*pos)) {
      return false;  // Trailing non-space
    }
    pos++;
  }

  *result = v;
  return true;  // Trailing space is OK
}

int to_int(BigStr* s, int base) {
  int i;
  if (StringToInteger(s->data_, len(s), base, &i)) {
    return i;
  } else {
    throw Alloc<ValueError>();
  }
}

int to_int(BigStr* s) {
  int i;
  if (StringToInteger(s->data_, len(s), 10, &i)) {
    return i;
  } else {
    throw Alloc<ValueError>();
  }
}

BigStr* chr(int i) {
  // NOTE: i should be less than 256, in which we could return an object from
  // GLOBAL_STR() pool, like StrIter
  auto result = NewStr(1);
  result->data_[0] = i;
  return result;
}

int ord(BigStr* s) {
  assert(len(s) == 1);
  // signed to unsigned conversion, so we don't get values like -127
  uint8_t c = static_cast<uint8_t>(s->data_[0]);
  return c;
}

bool to_bool(BigStr* s) {
  return len(s) != 0;
}

double to_float(int i) {
  return static_cast<double>(i);
}

double to_float(BigStr* s) {
  char* begin = s->data_;
  char* end = begin + len(s);

  errno = 0;
  double result = strtod(begin, &end);

  if (errno == ERANGE) {  // error: overflow or underflow
    if (result >= HUGE_VAL) {
      return INFINITY;
    } else if (result <= -HUGE_VAL) {
      return -INFINITY;
    } else if (-DBL_MIN <= result && result <= DBL_MIN) {
      return 0.0;
    } else {
      FAIL("Invalid value after ERANGE");
    }
  }
  if (end == begin) {  // error: not a floating point number
    throw Alloc<ValueError>();
  }

  return result;
}

// e.g. ('a' in 'abc')
bool str_contains(BigStr* haystack, BigStr* needle) {
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

BigStr* str_repeat(BigStr* s, int times) {
  // Python allows -1 too, and Oil used that
  if (times <= 0) {
    return kEmptyString;
  }
  int len_ = len(s);
  int new_len = len_ * times;
  BigStr* result = NewStr(new_len);

  char* dest = result->data_;
  for (int i = 0; i < times; i++) {
    memcpy(dest, s->data_, len_);
    dest += len_;
  }
  return result;
}

// for os_path.join()
// NOTE(Jesse): Perfect candidate for BoundedBuffer
BigStr* str_concat3(BigStr* a, BigStr* b, BigStr* c) {
  int a_len = len(a);
  int b_len = len(b);
  int c_len = len(c);

  int new_len = a_len + b_len + c_len;
  BigStr* result = NewStr(new_len);
  char* pos = result->data_;

  memcpy(pos, a->data_, a_len);
  pos += a_len;

  memcpy(pos, b->data_, b_len);
  pos += b_len;

  memcpy(pos, c->data_, c_len);

  assert(pos + c_len == result->data_ + new_len);

  return result;
}

BigStr* str_concat(BigStr* a, BigStr* b) {
  int a_len = len(a);
  int b_len = len(b);
  int new_len = a_len + b_len;
  BigStr* result = NewStr(new_len);
  char* buf = result->data_;

  memcpy(buf, a->data_, a_len);
  memcpy(buf + a_len, b->data_, b_len);

  return result;
}

//
// Comparators
//

bool str_equals(BigStr* left, BigStr* right) {
  // Fast path for identical strings.  String deduplication during GC could
  // make this more likely.  String interning could guarantee it, allowing us
  // to remove memcmp().
  if (left == right) {
    return true;
  }

  if (left == nullptr || right == nullptr) {
    return false;
  }

  // obj_len equal implies string lengths are equal

  if (left->len_ == right->len_) {
    // assert(len(left) == len(right));
    return memcmp(left->data_, right->data_, left->len_) == 0;
  }

  return false;
}

bool maybe_str_equals(BigStr* left, BigStr* right) {
  if (left && right) {
    return str_equals(left, right);
  }

  if (!left && !right) {
    return true;  // None == None
  }

  return false;  // one is None and one is a BigStr*
}

// TODO(Jesse): Make an inline version of this
bool are_equal(BigStr* left, BigStr* right) {
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
bool keys_equal(BigStr* left, BigStr* right) {
  return are_equal(left, right);
}

bool are_equal(Tuple2<BigStr*, int>* t1, Tuple2<BigStr*, int>* t2) {
  bool result = are_equal(t1->at0(), t2->at0());
  result = result && (t1->at1() == t2->at1());
  return result;
}

bool are_equal(Tuple2<int, int>* t1, Tuple2<int, int>* t2) {
  return t1->at0() == t2->at0() && t1->at1() == t2->at1();
}

bool keys_equal(Tuple2<int, int>* t1, Tuple2<int, int>* t2) {
  return are_equal(t1, t2);
}

bool keys_equal(Tuple2<BigStr*, int>* t1, Tuple2<BigStr*, int>* t2) {
  return are_equal(t1, t2);
}

bool str_equals0(const char* c_string, BigStr* s) {
  int n = strlen(c_string);
  if (len(s) == n) {
    return memcmp(s->data_, c_string, n) == 0;
  } else {
    return false;
  }
}

int hash(BigStr* s) {
  return s->hash(fnv1);
}

int max(int a, int b) {
  return std::max(a, b);
}

int max(List<int>* elems) {
  int n = len(elems);
  if (n < 1) {
    throw Alloc<ValueError>();
  }

  int ret = elems->at(0);
  for (int i = 0; i < n; ++i) {
    int cand = elems->at(i);
    if (cand > ret) {
      ret = cand;
    }
  }

  return ret;
}
