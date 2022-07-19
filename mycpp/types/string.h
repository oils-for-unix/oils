#include <algorithm> // min max

#if MYLIB_LEAKY

using mylib::AllocStr;
using mylib::NewList;
using gc_heap::gHeap;
using gc_heap::Local;

constexpr int kStrHeaderSize = offsetof(Str, data_);

#else

using gc_heap::Str;
using gc_heap::List;
using gc_heap::AllocStr;
using gc_heap::NewList;
using gc_heap::kStrHeaderSize;
using gc_heap::gHeap;
using gc_heap::Local;

#endif

inline Str* AllocStr_(char *buf, int len) {
  int obj_len = kStrHeaderSize + len + 1;  // NUL terminator

  char* temp = (char*)malloc(len);
  memcpy(temp, buf, len);

  void* place = gHeap.Allocate(obj_len);
#if MYLIB_LEAKY
  auto s = new (place) Str(0, 0);
#else
  auto s = new (place) Str();
#endif

  memcpy((void*)s->data_, temp, len);
  free(temp);

  s->SetObjLen(obj_len);  // So the GC can copy it
  return s;
}

Str* slice(Local<Str> to_slice, int begin, int end) {
  int length = len(to_slice);
  begin = std::min(begin, length);
  end = std::min(end, length);

  assert(begin <= length);
  assert(end <= length);

  if (begin < 0) {
    begin = length + begin;
  }

  if (end < 0) {
    end = length + end;
  }

  begin = std::min(begin, length);
  end = std::min(end, length);

  begin = std::max(begin, 0);
  end = std::max(end, 0);

  assert(begin >= 0);
  assert(begin <= length);

  assert(end >= 0);
  assert(end <= length);

  int new_len = end - begin;

  // Tried to use std::clamp() here but we're not compiling against cxx-17
  new_len = std::max(new_len, 0);
  new_len = std::min(new_len, length);

  /* printf("len(%d) [%d, %d] newlen(%d)\n",  length, begin, end, new_len); */

  assert(new_len >= 0);
  assert(new_len <= length);

  Str *Result = AllocStr(new_len);
  memcpy((void*)Result->data_, to_slice->data_ + begin, new_len);

  assert(Result->data_[new_len] == '\0');
  return Result;
}

// s[begin:]
Str* Str::slice(int begin) {
  int length = len(this);

  if (begin == 0) {
    return this;  // s[i:] where i == 0 is common in here docs
  }
  if (begin < 0) {
    begin = length + begin;
  }
  return ::slice(Local<Str>(this), begin, length);
}

// s[begin:end]
Str* Str::slice(int begin, int end) {
  return ::slice(this, begin, end);
}


List<Str*>* split(Local<Str> to_split, Str* sep) {
  int length = len(to_split);

  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  if (length == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return NewList<Str*>({AllocStr("")});
  }

  auto result = NewList<Str*>({});

  int n = length;
  const char* pos = to_split->data_;
  const char* end = to_split->data_ + length;

  while (true) {
    const char* new_pos = static_cast<const char*>(memchr(pos, sep_char, n));
    if (new_pos == nullptr) {
      result->append(AllocStr_((char*)pos, end - pos));  // rest of the string
      break;
    }
    int new_len = new_pos - pos;

    result->append(AllocStr_((char*)pos, new_len));
    n -= new_len + 1;
    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(AllocStr(""));
      break;
    }
  }

  return result;
}

List<Str*>* Str::split(Local<Str> sep) {
  return ::split(this, sep);
}

Str* replace(Local<Str> target, Local<Str> old, Local<Str> new_str) {
  log("replacing (%s) (%s) (%s)", target->data_, old->data_, new_str->data_);

  const char* old_data = old->data_;
  int old_len = len(old);
  const char* last_possible = target->data_ + len(target) - old_len;

  const char* p_this = target->data_;  // advances through 'this'

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
    return target;  // Reuse the string if there were no replacements
  }

  int result_len =
      len(target) - (replace_count * old_len) + (replace_count * len(new_str));

  char* result = static_cast<char*>(malloc(result_len + 1));  // +1 for NUL

  const char* new_data = new_str->data_;
  const size_t new_len = len(new_str);

  // Second pass: Copy pieces into 'result'
  p_this = target->data_;           // back to beginning
  char* p_result = result;  // advances through 'result'

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
  memcpy(p_result, p_this, target->data_ + len(target) - p_this);  // last part of string
  result[result_len] = '\0';                        // NUL terminate
  /* free(result); */


  Local<Str> thing = AllocStr(result, result_len);
  log("result(%s)", result);
  return thing;
}

Str* Str::replace(Local<Str> old, Local<Str> new_str) {
  log("replace thunk");
  Str* Result = ::replace(this, old, new_str);
  log("replace thunk complete");
  return Result;
}
