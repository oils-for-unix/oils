#ifndef OLDSTL_CONTAINERS_H
#define OLDSTL_CONTAINERS_H

#ifndef OLDSTL_BINDINGS
  #error \
      "This file contains definitions for OLDSTL containers.  If you wanted a gc'd container build, include gc_containers.h"
#endif

#include <assert.h>
#include <ctype.h>   // isalpha(), isdigit()
#include <stdlib.h>  // malloc
#include <string.h>  // strlen

#include <algorithm>  // sort() is templated
// https://stackoverflow.com/questions/3882346/forward-declare-file
#include <climits>  // CHAR_BIT
#include <cstdint>
#include <cstdio>  // FILE*
#include <initializer_list>
#include <vector>

#include "common.h"

#ifdef DUMB_ALLOC
  #include "cpp/dumb_alloc.h"
  #define malloc dumb_malloc
  #define free dumb_free
#endif

#define GLOBAL_STR(name, val) Str* name = StrFromC(val, sizeof(val) - 1)
#define GLOBAL_LIST(T, N, name, array) List<T>* name = new List<T>(array);

class Obj;

struct Heap {
  void Init(int byte_count) {
  }

  void Bump() {
  }

  void Collect() {
  }

  void* Allocate(int num_bytes) {
    return calloc(num_bytes, 1);
  }

  void PushRoot(Obj** p) {
  }

  void PopRoot() {
  }
};

extern Heap gHeap;

// clang-format off
#include "mycpp/gc_tag.h"
#include "mycpp/gc_obj.h"
#include "mycpp/gc_alloc.h"
// clang-format on

struct StackRoots {
  StackRoots(std::initializer_list<void*> roots) {
  }
};

template <class T>
class List;

template <class K, class V>
class Dict;

template <class K, class V>
class DictIter;

// clang-format off
#include "mycpp/tuple_types.h"
#include "mycpp/error_types.h"
#include "mycpp/gc_str.h"
#include "mycpp/oldstl_mylib.h" // mylib namespace
// clang-format on

extern Str* kEmptyString;

//
// Data Types
//

// TODO: Rewrite without vector<>, so we don't depend on libstdc++.
template <class T>
class List : public Obj {
 public:
  // Note: constexpr doesn't work because the std::vector destructor is
  // nontrivial
  List() : Obj(Tag::FixedSize, kZeroMask, 0), v_() {
    // Note: this seems to INCREASE the number of 'new' calls.  I guess because
    // many 'spids' lists aren't used?
    // v_.reserve(64);
  }

  // Used by list_repeat
  List(T item, int n) : Obj(Tag::FixedSize, kZeroMask, 0), v_(n, item) {
  }

  List(std::initializer_list<T> init)
      : Obj(Tag::FixedSize, kZeroMask, 0), v_() {
    for (T item : init) {
      v_.push_back(item);
    }
  }

  // a[-1] = 42 becomes a->set(-1, 42);
  void set(int index, T value) {
    if (index < 0) {
      index = v_.size() + index;
    }
    v_[index] = value;
  }

  // L[i]
  T index_(int i) const {
    if (i < 0) {
      // User code doesn't result in mylist[-1], but Oil's own code does
      int j = v_.size() + i;
      return v_.at(j);
    }
    return v_.at(i);  // checked version
  }

  // L.index(i) -- Python method
  int index(T value) const {
    int len = v_.size();
    for (int i = 0; i < len; i++) {
      // TODO: this doesn't work for strings!
      if (v_[i] == value) {
        return i;
      }
    }
    throw new ValueError();
  }

  // L[begin:]
  List* slice(int begin) {
    if (begin == 0) {
      return this;
    }
    if (begin < 0) {
      begin = v_.size() + begin;
    }

    List* result = new List();
    int len = v_.size();
    for (int i = begin; i < len; i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }
  // L[begin:end]
  // TODO: Can this be optimized?
  List* slice(int begin, int end) {
    if (begin < 0) {
      begin = v_.size() + begin;
    }
    if (end < 0) {
      end = v_.size() + end;
    }

    List* result = new List();
    for (int i = begin; i < end; i++) {
      result->v_.push_back(v_[i]);
    }
    return result;
  }

  void append(T item) {
#ifdef ALLOC_LOG
    // we can post process this format to find large lists
    // except when they're constants, but that's OK?
    printf("%p %zu\n", this, v_.size());
#endif

    v_.push_back(item);
  }

  void extend(List<T>* items) {
    // Note: C++ idioms would be v_.insert() or std::copy, but we're keeping it
    // simple.
    //
    // We could optimize this for the small cases Oil has?  I doubt it's a
    // bottleneck anywhere.
    int len = items->v_.size();
    for (int i = 0; i < len; ++i) {
      v_.push_back(items->v_[i]);
    }
  }

  // Reconsider?
  // https://stackoverflow.com/questions/12600330/pop-back-return-value
  T pop() {
    assert(!v_.empty());
    T result = v_.back();
    v_.pop_back();
    return result;
  }

  // Used in osh/word_parse.py to remove from front
  // TODO: Don't accept arbitrary index?
  T pop(int index) {
    if (v_.size() == 0) {
      // TODO(Jesse): Probably shouldn't crash if we try to pop a List with
      // nothing on it
      InvalidCodePath();
    }

    T result = v_.at(index);
    v_.erase(v_.begin() + index);
    return result;

    /*
    Implementation without std::vector
    assert(index == 0);
    for (int i = 1; i < v_.size(); ++i) {
      v_[i-1] = v_[i];
    }
    v_.pop_back();
    */
  }

  void clear() {
    v_.clear();
  }

  void sort() {
    mysort(&v_);
  }

  // in osh/string_ops.py
  void reverse() {
    int n = v_.size();
    for (int i = 0; i < n / 2; ++i) {
      // log("swapping %d and %d", i, n-i);
      T tmp = v_[i];
      int j = n - 1 - i;
      v_[i] = v_[j];
      v_[j] = tmp;
    }
  }

  // private:
  std::vector<T> v_;  // ''.join accesses this directly
};

// Same as GC APIs

template <typename T>
List<T>* NewList() {
  return new List<T>();
}

template <typename T>
List<T>* NewList(std::initializer_list<T> init) {
  return new List<T>(init);
}

template <class T>
class ListIter {
 public:
  explicit ListIter(List<T>* L) : L_(L), i_(0) {
  }
  void Next() {
    i_++;
  }
  bool Done() {
    // "unsigned size_t was a mistake"
    return i_ >= static_cast<int>(L_->v_.size());
  }
  T Value() {
    return L_->v_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

// TODO: Does using pointers rather than indices make this more efficient?
template <class T>
class ReverseListIter {
 public:
  explicit ReverseListIter(List<T>* L) : L_(L), i_(L_->v_.size() - 1) {
  }
  void Next() {
    i_--;
  }
  bool Done() {
    return i_ < 0;
  }
  T Value() {
    return L_->v_[i_];
  }

 private:
  List<T>* L_;
  int i_;
};

// TODO: A proper dict index should get rid of this unusual sentinel scheme.
// The index can be -1 on deletion, regardless of the type of the key.

template <class K, class V>
void dict_next(DictIter<K, V>* it, const std::vector<std::pair<K, V>>& items) {
  ++it->i_;
}

template <class V>
void dict_next(DictIter<Str*, V>* it,
               const std::vector<std::pair<Str*, V>>& items) {
  while (true) {
    ++it->i_;
    if (it->Done()) {
      break;
    }
    if (items[it->i_].first) {  // not nullptr
      break;
    }
  }
}

template <class K, class V>
bool dict_done(DictIter<K, V>* it, const std::vector<std::pair<K, V>>& items) {
  int n = items.size();
  return it->i_ >= n;
}

template <class V>
bool dict_done(DictIter<Str*, V>* it,
               const std::vector<std::pair<Str*, V>>& items) {
  int n = items.size();
  if (it->i_ >= n) {
    return true;
  }
  for (int j = it->i_; j < n; ++j) {
    if (items[j].first) {  // there's still something left
      return false;
    }
  }
  return true;
}

template <class K, class V>
class DictIter {
 public:
  explicit DictIter(Dict<K, V>* D) : D_(D), i_(0) {
  }
  void Next() {
    dict_next(this, D_->items_);
  }
  bool Done() {
    return dict_done(this, D_->items_);
  }
  K Key() {
    return D_->items_[i_].first;
  }
  V Value() {
    return D_->items_[i_].second;
  }

  Dict<K, V>* D_;
  int i_;
};

inline bool str_equals(Str* left, Str* right) {
  if (len(left) == len(right)) {
    return memcmp(left->data_, right->data_, len(left)) == 0;
  } else {
    return false;
  }
}

// Specialized functions
template <class V>
int find_by_key(const std::vector<std::pair<Str*, V>>& items, Str* key) {
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    Str* s = items[i].first;  // nullptr for deleted entries
    if (s && str_equals(s, key)) {
      return i;
    }
  }
  return -1;
}

template <class V>
int find_by_key(const std::vector<std::pair<int, V>>& items, int key) {
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    if (items[i].first == key) {
      return i;
    }
  }
  return -1;
}

template <class V>
List<Str*>* dict_keys(const std::vector<std::pair<Str*, V>>& items) {
  auto result = new List<Str*>();
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    Str* s = items[i].first;  // nullptr for deleted entries
    if (s) {
      result->append(s);
    }
  }
  return result;
}

template <class V>
List<V>* dict_values(const std::vector<std::pair<Str*, V>>& items) {
  auto result = new List<V>();
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    auto& pair = items[i];
    if (pair.first) {
      result->append(pair.second);
    }
  }
  return result;
}

// Dict currently implemented by VECTOR OF PAIRS.  TODO: Use a real hash table,
// and measure performance.  The hash table has to beat this for small cases!
template <class K, class V>
class Dict : public Obj {
 public:
  Dict() : Obj(Tag::FixedSize, kZeroMask, 0), items_() {
  }

  // Dummy
  Dict(std::initializer_list<K> keys, std::initializer_list<V> values)
      : Obj(Tag::FixedSize, kZeroMask, 0), items_() {
  }

  // d[key] in Python: raises KeyError if not found
  V index_(K key) {
    int pos = find(key);
    if (pos == -1) {
      throw new KeyError();
    } else {
      return items_[pos].second;
    }
  }

  // Get a key.
  // Returns nullptr if not found (Can't use this for non-pointer types?)
  V get(K key) {
    int pos = find(key);
    if (pos == -1) {
      return nullptr;
    } else {
      return items_[pos].second;
    }
  }

  // Get a key, but return a default if not found.
  // expr_parse.py uses this with OTHER_BALANCE
  V get(K key, V default_val) {
    int pos = find(key);
    if (pos == -1) {
      return default_val;
    } else {
      return items_[pos].second;
    }
  }

  // d->set(key, val) is like (*d)[key] = val;
  void set(K key, V val) {
    int pos = find(key);
    if (pos == -1) {
      items_.push_back(std::make_pair(key, val));
    } else {
      items_[pos].second = val;
    }
  }

  void remove(K key) {
    mylib::dict_remove(this, key);
  }

  List<K>* keys() {
    return dict_keys(items_);
  }

  // For AssocArray transformations
  List<V>* values() {
    return dict_values(items_);
  }

  void clear() {
    items_.clear();
  }

  // std::unordered_map<K, V> m_;
  std::vector<std::pair<K, V>> items_;

 private:
  // returns the position in the array
  int find(K key) {
    return find_by_key(items_, key);
  }
};

template <typename K, typename V>
Dict<K, V>* NewDict() {
  auto self = Alloc<Dict<K, V>>();
  return self;
}

template <typename K, typename V>
Dict<K, V>* NewDict(std::initializer_list<K> keys,
                    std::initializer_list<V> values) {
  // TODO(Jesse): Is this NotImplemented() or InvalidCodePath() ?
  assert(0);  // Uncalled
}

//
// Overloaded free function len()
//

template <typename T>
inline int len(const List<T>* L) {
  return L->v_.size();
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  assert(0);
}

template <typename V>
inline int len(const Dict<Str*, V>* d) {
  int len = 0;
  int n = d->items_.size();
  for (int i = 0; i < n; ++i) {
    Str* s = d->items_[i].first;  // nullptr for deleted entries
    if (s) {
      len++;
    }
  }
  return len;
}

//
// Free functions
//

Str* str_concat(Str* a, Str* b);           // a + b when a and b are strings
Str* str_concat3(Str* a, Str* b, Str* c);  // for os_path::join()

Str* str_repeat(Str* s, int times);  // e.g. ' ' * 3

namespace id_kind_asdl {
enum class Kind;
};

inline bool are_equal(id_kind_asdl::Kind left, id_kind_asdl::Kind right);

inline bool are_equal(int left, int right) {
  return left == right;
}

inline bool are_equal(Str* left, Str* right) {
  return str_equals(left, right);
}

inline bool are_equal(Tuple2<Str*, int>* t1, Tuple2<Str*, int>* t2) {
  bool result = are_equal(t1->at0(), t2->at0());
  result = result && (t1->at1() == t2->at1());
  return result;
}

inline bool str_equals0(const char* c_string, Str* s) {
  int n = strlen(c_string);
  if (len(s) == n) {
    return memcmp(s->data_, c_string, n) == 0;
  } else {
    return false;
  }
}

inline bool maybe_str_equals(Str* left, Str* right) {
  if (left && right) {
    return str_equals(left, right);
  }

  if (!left && !right) {
    return true;  // None == None
  }

  return false;  // one is None and one is a Str*
}

// TODO: There should be one str() and one repr() for every sum type, that
// dispatches on tag?  Or just repr()?

// Will need it for dict, but not tuple.
// inline int len(Dict* D) {
// }

// e.g. [None] * 3
template <typename T>
List<T>* list_repeat(T item, int times) {
  return new List<T>(item, times);
}

// list(L) copies the list
template <typename T>
List<T>* list(List<T>* other) {
  auto result = new List<T>();
  for (int i = 0; i < len(other); ++i) {
    result->set(i, other->index_(i));
  }
  return result;
}

template <typename T>
bool list_contains(List<T>* haystack, T needle) {
  int n = haystack->v_.size();
  for (int i = 0; i < n; ++i) {
    if (are_equal(haystack->index_(i), needle)) {
      return true;
    }
  }
  return false;
}

template <typename T>
bool list_contains(List<T>* haystack, T* needle) {
  bool result = false;

  if (needle) {
    result = list_contains(haystack, *needle);
  }

  return result;
}

template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return find_by_key(haystack->items_, needle) != -1;
}

template <typename V>
List<Str*>* sorted(Dict<Str*, V>* d) {
  auto keys = d->keys();
  keys->sort();
  return keys;
}

inline int int_cmp(int a, int b) {
  if (a == b) {
    return 0;
  }
  return a < b ? -1 : 1;
}

// Used by [[ a > b ]] and so forth
inline int str_cmp(Str* a, Str* b) {
  int min = std::min(len(a), len(b));
  if (min == 0) {
    return int_cmp(len(a), len(b));
  }
  int comp = memcmp(a->data_, b->data_, min);
  if (comp == 0) {
    return int_cmp(len(a), len(b));  // tiebreaker
  }
  return comp;
}

// Hm std::sort() just needs true/false, not 0, 1, 1.
inline bool _cmp(Str* a, Str* b) {
  return str_cmp(a, b) < 0;
}

// specialization for Str only
inline void mysort(std::vector<Str*>* v) {
  std::sort(v->begin(), v->end(), _cmp);
}

#endif  // OLDSTL_CONTAINERS_H
