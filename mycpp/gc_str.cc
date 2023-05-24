#include "mycpp/gc_str.h"

#include <ctype.h>  // isalpha(), isdigit()
#include <stdarg.h>

#include <regex>

#include "mycpp/common.h"
#include "mycpp/gc_alloc.h"     // NewStr()
#include "mycpp/gc_builtins.h"  // StringToInteger()
#include "mycpp/gc_list.h"      // join(), split() use it

GLOBAL_STR(kEmptyString, "");

static const std::regex gStrFmtRegex("([^%]*)(?:%(-?[0-9]*)(.))?");
static const int kMaxFmtWidth = 256;  // arbitrary...

int Str::find(Str* needle, int pos) {
  int len_ = len(this);
  assert(len(needle) == 1);  // Oil's usage
  char c = needle->data_[0];
  for (int i = pos; i < len_; ++i) {
    if (data_[i] == c) {
      return i;
    }
  }
  return -1;
}

int Str::rfind(Str* needle) {
  int len_ = len(this);
  assert(len(needle) == 1);  // Oil's usage
  char c = needle->data_[0];
  for (int i = len_ - 1; i >= 0; --i) {
    if (data_[i] == c) {
      return i;
    }
  }
  return -1;
}

bool Str::isdigit() {
  int n = len(this);
  if (n == 0) {
    return false;  // special case
  }
  for (int i = 0; i < n; ++i) {
    if (!::isdigit(data_[i])) {
      return false;
    }
  }
  return true;
}

bool Str::isalpha() {
  int n = len(this);
  if (n == 0) {
    return false;  // special case
  }
  for (int i = 0; i < n; ++i) {
    if (!::isalpha(data_[i])) {
      return false;
    }
  }
  return true;
}

// e.g. for osh/braces.py
bool Str::isupper() {
  int n = len(this);
  if (n == 0) {
    return false;  // special case
  }
  for (int i = 0; i < n; ++i) {
    if (!::isupper(data_[i])) {
      return false;
    }
  }
  return true;
}

bool Str::startswith(Str* s) {
  int n = len(s);
  if (n > len(this)) {
    return false;
  }
  return memcmp(data_, s->data_, n) == 0;
}

bool Str::endswith(Str* s) {
  int len_s = len(s);
  int len_this = len(this);
  if (len_s > len_this) {
    return false;
  }
  const char* start = data_ + len_this - len_s;
  return memcmp(start, s->data_, len_s) == 0;
}

// Get a string with one character
Str* Str::index_(int i) {
  int len_ = len(this);
  if (i < 0) {
    i = len_ + i;
  }
  assert(i >= 0);
  assert(i < len_);  // had a problem here!

  Str* result = NewStr(1);
  result->data_[0] = data_[i];
  return result;
}

// s[begin:end:step]
Str* Str::slice(int begin, int end, int step) {
  int len_ = len(this);
  begin = std::min(begin, len_);
  end = std::min(end, len_);

  assert(begin <= len_);
  assert(end <= len_);

  if (begin < 0) {
    begin = len_ + begin;
  }

  if (end < 0) {
    end = len_ + end;
  }

  begin = std::min(begin, len_);
  end = std::min(end, len_);

  begin = std::max(begin, 0);
  end = std::max(end, 0);

  assert(begin >= 0);
  assert(begin <= len_);

  assert(end >= 0);
  assert(end <= len_);

  int astep = std::abs(step);
  int new_len = (end - begin);
  new_len = new_len / astep + (new_len % astep);

  // Tried to use std::clamp() here but we're not compiling against cxx-17
  new_len = std::max(new_len, 0);
  new_len = std::min(new_len, len_);

  // printf("len(%d) [%d, %d] newlen(%d)\n",  len_, begin, end, new_len);

  assert(new_len >= 0);
  assert(new_len <= len_);

  Str* result = NewStr(new_len + 1);
  // step might be negative
  int j = 0;
  for (int i = begin; begin <= i && i < end; i += step, j++) {
    result->data_[j] = data_[i];
  }
  result->data_[new_len] = '\0';

  return result;
}

// s[begin:end]
Str* Str::slice(int begin, int end) {
  int len_ = len(this);
  begin = std::min(begin, len_);
  end = std::min(end, len_);

  assert(begin <= len_);
  assert(end <= len_);

  if (begin < 0) {
    begin = len_ + begin;
  }

  if (end < 0) {
    end = len_ + end;
  }

  begin = std::min(begin, len_);
  end = std::min(end, len_);

  begin = std::max(begin, 0);
  end = std::max(end, 0);

  assert(begin >= 0);
  assert(begin <= len_);

  assert(end >= 0);
  assert(end <= len_);

  int new_len = end - begin;

  // Tried to use std::clamp() here but we're not compiling against cxx-17
  new_len = std::max(new_len, 0);
  new_len = std::min(new_len, len_);

  // printf("len(%d) [%d, %d] newlen(%d)\n",  len_, begin, end, new_len);

  assert(new_len >= 0);
  assert(new_len <= len_);

  Str* result = NewStr(new_len);
  memcpy(result->data_, data_ + begin, new_len);

  return result;
}

// s[begin:]
Str* Str::slice(int begin) {
  int len_ = len(this);
  if (begin == 0) {
    return this;  // s[i:] where i == 0 is common in here docs
  }
  if (begin < 0) {
    begin = len_ + begin;
  }
  return slice(begin, len_);
}

// Used by 'help' builtin and --help, neither of which translate yet.

List<Str*>* Str::splitlines(bool keep) {
  assert(keep == true);
  FAIL(kNotImplemented);
}

Str* Str::upper() {
  int len_ = len(this);
  Str* result = NewStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = toupper(data_[char_index]);
  }
  return result;
}

Str* Str::lower() {
  int len_ = len(this);
  Str* result = NewStr(len_);
  char* buffer = result->data();
  for (int char_index = 0; char_index < len_; ++char_index) {
    buffer[char_index] = tolower(data_[char_index]);
  }
  return result;
}

Str* Str::ljust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int len_ = len(this);
  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    Str* result = NewStr(width);
    char c = fillchar->data_[0];
    memcpy(result->data_, data_, len_);
    for (int i = len_; i < width; ++i) {
      result->data_[i] = c;
    }
    return result;
  }
}

Str* Str::rjust(int width, Str* fillchar) {
  assert(len(fillchar) == 1);

  int len_ = len(this);
  int num_fill = width - len_;
  if (num_fill < 0) {
    return this;
  } else {
    Str* result = NewStr(width);
    char c = fillchar->data_[0];
    for (int i = 0; i < num_fill; ++i) {
      result->data_[i] = c;
    }
    memcpy(result->data_ + num_fill, data_, len_);
    return result;
  }
}

Str* Str::replace(Str* old, Str* new_str) {
  // log("replacing %s with %s", old_data, new_str->data_);
  const char* old_data = old->data_;

  int this_len = len(this);
  int old_len = len(old);

  const char* last_possible = data_ + this_len - old_len;

  const char* p_this = data_;  // advances through 'this'

  // First pass: Calculate number of replacements, and hence new length
  int replace_count = 0;
  while (p_this <= last_possible) {
    if (memcmp(p_this, old_data, old_len) == 0) {  // equal
      replace_count++;
      p_this += old_len;
    } else {
      p_this++;
    }
  }

  // log("replacements %d", replace_count);

  if (replace_count == 0) {
    return this;  // Reuse the string if there were no replacements
  }

  int new_str_len = len(new_str);
  int result_len =
      this_len - (replace_count * old_len) + (replace_count * new_str_len);

  Str* result = NewStr(result_len);

  const char* new_data = new_str->data_;
  const size_t new_len = new_str_len;

  // Second pass: Copy pieces into 'result'
  p_this = data_;                  // back to beginning
  char* p_result = result->data_;  // advances through 'result'

  while (p_this <= last_possible) {
    // Note: would be more efficient if we remembered the match positions
    if (memcmp(p_this, old_data, old_len) == 0) {  // equal
      memcpy(p_result, new_data, new_len);         // Copy from new_str
      p_result += new_len;
      p_this += old_len;
    } else {  // copy 1 byte
      *p_result = *p_this;
      p_result++;
      p_this++;
    }
  }
  memcpy(p_result, p_this, data_ + this_len - p_this);  // last part of string
  return result;
}

enum class StripWhere {
  Left,
  Right,
  Both,
};

const int kWhitespace = -1;

bool OmitChar(uint8_t ch, int what) {
  if (what == kWhitespace) {
    return isspace(ch);
  } else {
    return what == ch;
  }
}

// StripAny is modeled after CPython's do_strip() in stringobject.c, and can
// implement 6 functions:
//
//   strip / lstrip / rstrip
//   strip(char) / lstrip(char) / rstrip(char)
//
// Args:
//   where: which ends to strip from
//   what: kWhitespace, or an ASCII code 0-255

Str* StripAny(Str* s, StripWhere where, int what) {
  int length = len(s);
  const char* char_data = s->data();

  int i = 0;
  if (where != StripWhere::Right) {
    while (i < length && OmitChar(char_data[i], what)) {
      i++;
    }
  }

  int j = length;
  if (where != StripWhere::Left) {
    do {
      j--;
    } while (j >= i && OmitChar(char_data[j], what));
    j++;
  }

  if (i == j) {  // Optimization to reuse existing object
    return kEmptyString;
  }

  if (i == 0 && j == length) {  // nothing stripped
    return s;
  }

  // Note: makes a copy in leaky version, and will in GC version too
  int new_len = j - i;
  Str* result = NewStr(new_len);
  memcpy(result->data(), s->data() + i, new_len);
  return result;
}

Str* Str::strip() {
  return StripAny(this, StripWhere::Both, kWhitespace);
}

// Used for CommandSub in osh/cmd_exec.py
Str* Str::rstrip(Str* chars) {
  assert(len(chars) == 1);
  int c = chars->data_[0];
  return StripAny(this, StripWhere::Right, c);
}

Str* Str::rstrip() {
  return StripAny(this, StripWhere::Right, kWhitespace);
}

Str* Str::lstrip(Str* chars) {
  assert(len(chars) == 1);
  int c = chars->data_[0];
  return StripAny(this, StripWhere::Left, c);
}

Str* Str::lstrip() {
  return StripAny(this, StripWhere::Left, kWhitespace);
}

Str* Str::join(List<Str*>* items) {
  int length = 0;

  int num_parts = len(items);

  // " ".join([]) == ""
  if (num_parts == 0) {
    return kEmptyString;
  }

  // Common case
  // 'anything'.join(["foo"]) == "foo"
  if (num_parts == 1) {
    return items->index_(0);
  }

  for (int i = 0; i < num_parts; ++i) {
    length += len(items->index_(i));
  }
  // add length of all the separators
  int this_len = len(this);
  length += this_len * (num_parts - 1);

  Str* result = NewStr(length);
  char* p_result = result->data_;  // advances through

  for (int i = 0; i < num_parts; ++i) {
    // log("i %d", i);
    if (i != 0 && this_len) {             // optimize common case of ''.join()
      memcpy(p_result, data_, this_len);  // copy the separator
      p_result += this_len;
      // log("this_len %d", this_len);
    }

    int n = len(items->index_(i));
    // log("n: %d", n);
    memcpy(p_result, items->index_(i)->data_, n);  // copy the list item
    p_result += n;
  }

  return result;
}

static void AppendPart(List<Str*>* result, Str* s, int left, int right) {
  int new_len = right - left;
  Str* part;
  if (new_len == 0) {
    part = kEmptyString;
  } else {
    part = NewStr(new_len);
    memcpy(part->data_, s->data_ + left, new_len);
  }
  result->append(part);
}

// Split Str into List<Str*> of parts separated by 'sep'.
// The code structure is taken from CPython's Objects/stringlib/split.h.
List<Str*>* Str::split(Str* sep, int max_split) {
  DCHECK(sep != nullptr);
  DCHECK(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  int str_len = len(this);
  if (str_len == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return NewList<Str*>({kEmptyString});
  }

  List<Str*>* result = NewList<Str*>({});
  int left = 0;
  int right = 0;
  int num_parts = 0;  // 3 splits results in 4 parts

  while (right < str_len && num_parts < max_split) {
    // search for separator
    for (; right < str_len; right++) {
      if (data_[right] == sep_char) {
        AppendPart(result, this, left, right);
        right++;
        left = right;
        num_parts++;
        break;
      }
    }
  }
  if (num_parts == 0) {  // Optimization when there is no split
    result->append(this);
  } else if (left <= str_len) {  // Last part
    AppendPart(result, this, left, str_len);
  }

  return result;
}

List<Str*>* Str::split(Str* sep) {
  return this->split(sep, len(this));
}

static inline Str* _StrFormat(const char* fmt, int fmt_len, va_list args) {
  auto beg = std::cregex_iterator(fmt, fmt + fmt_len, gStrFmtRegex);
  auto end = std::cregex_iterator();

  char int_buf[kMaxFmtWidth];
  std::string buf;
  for (std::cregex_iterator it = beg; it != end; ++it) {
    const std::cmatch& match = *it;

    const std::csub_match& lit_m = match[1];
    assert(lit_m.matched);
    const std::string& lit_s = lit_m.str();
    buf.append(lit_s);

    int width = 0;
    bool zero_pad = false;
    bool pad_back = false;
    const std::csub_match& width_m = match[2];
    const std::string& width_s = width_m.str();
    if (width_m.matched && !width_s.empty()) {
      if (width_s[0] == '0') {
        zero_pad = true;
        assert(width_s.size() > 1);
        assert(StringToInteger(width_s.c_str() + 1, width_s.size() - 1, 10,
                               &width));
      } else {
        assert(StringToInteger(width_s.c_str(), width_s.size(), 10, &width));
      }
      if (width < 0) {
        pad_back = true;
        width *= -1;
      }
      assert(width >= 0 && width < kMaxFmtWidth);
    }

    char const* str_to_add = nullptr;
    int add_len = 0;
    const std::csub_match& code_m = match[3];
    const std::string& code_s = code_m.str();
    if (!code_m.matched) {
      assert(!width_m.matched);  // python errors on invalid format operators
      break;
    }
    assert(code_s.size() == 1);
    switch (code_s[0]) {
    case '%': {
      str_to_add = code_s.c_str();
      add_len = 1;
      break;
    }
    case 's': {
      Str* s = va_arg(args, Str*);
      // Check type unconditionally because mycpp doesn't always check it
      CHECK(ObjHeader::FromObject(s)->type_tag == TypeTag::Str);

      str_to_add = s->data();
      add_len = len(s);
      zero_pad = false;  // python ignores the 0 directive for strings
      break;
    }
    case 'r': {
      Str* s = va_arg(args, Str*);
      // Check type unconditionally because mycpp doesn't always check it
      CHECK(ObjHeader::FromObject(s)->type_tag == TypeTag::Str);

      s = repr(s);
      str_to_add = s->data();
      add_len = len(s);
      zero_pad = false;  // python ignores the 0 directive for strings
      break;
    }
    case 'd':  // fallthrough
    case 'o': {
      int d = va_arg(args, int);
      add_len = snprintf(int_buf, kMaxFmtWidth,
                         match.str().c_str() + lit_s.size(), d);
      assert(add_len > 0);
      str_to_add = int_buf;
      break;
    }
    default:
      assert(0);
      break;
    }
    assert(str_to_add != nullptr);

    if (pad_back) {
      buf.append(str_to_add, add_len);
    }
    if (add_len < width) {
      for (int i = 0; i < width - add_len; ++i) {
        buf.push_back(zero_pad ? '0' : ' ');
      }
    }
    if (!pad_back) {
      buf.append(str_to_add, add_len);
    }
  }

  return StrFromC(buf.c_str(), buf.size());
}

Str* StrIter::Value() {  // similar to index_()
  Str* result = NewStr(1);
  result->data_[0] = s_->data_[i_];
  DCHECK(result->data_[1] == '\0');
  return result;
}

Str* StrFormat(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  Str* ret = _StrFormat(fmt, strlen(fmt), args);
  va_end(args);
  return ret;
}

Str* StrFormat(Str* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  Str* ret = _StrFormat(fmt->data(), len(fmt), args);
  va_end(args);
  return ret;
}
