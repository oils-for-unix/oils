template <class K, class V>
class DictIter;

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

bool str_equals(Str* left, Str* right);

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
  auto result = NewList<Str*>();
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
  auto result = NewList<V>();
  int n = items.size();
  for (int i = 0; i < n; ++i) {
    auto& pair = items[i];
    if (pair.first) {
      result->append(pair.second);
    }
  }
  return result;
}

// d[key] in Python: raises KeyError if not found
template <typename K, typename V>
V Dict<K, V>::index_(K key) {
  int pos = find(key);
  if (pos == -1) {
    throw new KeyError();
  } else {
    return items_[pos].second;
  }
}

// Get a key.
// Returns nullptr if not found (Can't use this for non-pointer types?)
template <typename K, typename V>
V Dict<K, V>::get(K key) {
  int pos = find(key);
  if (pos == -1) {
    return nullptr;
  } else {
    return items_[pos].second;
  }
}

// Get a key, but return a default if not found.
// expr_parse.py uses this with OTHER_BALANCE
template <typename K, typename V>
V Dict<K, V>::get(K key, V default_val) {
  int pos = find(key);
  if (pos == -1) {
    return default_val;
  } else {
    return items_[pos].second;
  }
}

// d->set(key, val) is like (*d)[key] = val;
template <typename K, typename V>
void Dict<K, V>::set(K key, V val) {
  int pos = find(key);
  if (pos == -1) {
    items_.push_back(std::make_pair(key, val));
  } else {
    items_[pos].second = val;
  }
}

template <typename K, typename V>
void Dict<K, V>::remove(K key) {
  mylib::dict_remove(this, key);
}

template <typename K, typename V>
List<K>* Dict<K, V>::keys() {
  return dict_keys(items_);
}

// For AssocArray transformations
template <typename K, typename V>
List<V>* Dict<K, V>::values() {
  return dict_values(items_);
}

template <typename K, typename V>
void Dict<K, V>::clear() {
  items_.clear();
}

// returns the position in the array
template <typename K, typename V>
int Dict<K, V>::find(K key) {
  return find_by_key(items_, key);
}

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

template <typename K, typename V>
inline bool dict_contains(Dict<K, V>* haystack, K needle) {
  return find_by_key(haystack->items_, needle) != -1;
}


