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

