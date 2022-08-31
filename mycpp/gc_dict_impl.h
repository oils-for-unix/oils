#ifndef GC_DICT_IMPL
#define GC_DICT_IMPL

template <typename K, typename V>
void Dict<K, V>::reserve(int n) {
  auto self = this;
  Slab<int>* new_i = nullptr;
  Slab<K>* new_k = nullptr;
  Slab<V>* new_v = nullptr;
  StackRoots _roots({&self, &new_i, &new_k, &new_v});

  // log("--- reserve %d", capacity_);
  //
  if (self->capacity_ < n) {  // TODO: use load factor, not exact fit
    // calculate the number of keys and values we should have
    self->capacity_ = RoundUp(n + kCapacityAdjust) - kCapacityAdjust;

    // TODO: This is SPARSE.  How to compute a size that ensures a decent
    // load factor?
    int index_len = self->capacity_;
    new_i = NewSlab<int>(index_len);

    // For the linear search to work
    for (int i = 0; i < index_len; ++i) {
      new_i->items_[i] = kEmptyEntry;
    }

    // These are DENSE.
    new_k = NewSlab<K>(self->capacity_);
    new_v = NewSlab<V>(self->capacity_);

    if (self->keys_ != nullptr) {
      // Right now the index is the same size as keys and values.
      memcpy(new_i->items_, self->entry_->items_, self->len_ * sizeof(int));

      memcpy(new_k->items_, self->keys_->items_, self->len_ * sizeof(K));
      memcpy(new_v->items_, self->values_->items_, self->len_ * sizeof(V));
    }

    self->entry_ = new_i;
    self->keys_ = new_k;
    self->values_ = new_v;
  }
}

// d[key] in Python: raises KeyError if not found
template <typename K, typename V>
V Dict<K, V>::index_(K key) {
  int pos = position_of_key(key);
  if (pos == -1) {
    throw new KeyError();
  } else {
    return values_->items_[pos];
  }
}

// Get a key.
// Returns nullptr if not found (Can't use this for non-pointer types?)
template <typename K, typename V>
V Dict<K, V>::get(K key) {
  int pos = position_of_key(key);
  if (pos == -1) {
    return nullptr;
  } else {
    return values_->items_[pos];
  }
}

// Get a key, but return a default if not found.
// expr_parse.py uses this with OTHER_BALANCE
template <typename K, typename V>
V Dict<K, V>::get(K key, V default_val) {
  int pos = position_of_key(key);
  if (pos == -1) {
    return default_val;
  } else {
    return values_->items_[pos];
  }
}

template <typename K, typename V>
List<K>* Dict<K, V>::keys() {
  return ListFromDictSlab<K>(entry_, keys_, capacity_);
}

// For AssocArray transformations
template <typename K, typename V>
List<V>* Dict<K, V>::values() {
  return ListFromDictSlab<V>(entry_, values_, capacity_);
}

template <typename K, typename V>
void Dict<K, V>::clear() {
  // Maintain invariant
  for (int i = 0; i < capacity_; ++i) {
    entry_->items_[i] = kEmptyEntry;
  }

  memset(keys_->items_, 0, len_ * sizeof(K));    // zero for GC scan
  memset(values_->items_, 0, len_ * sizeof(V));  // zero for GC scan
  len_ = 0;
}

// Returns the position in the array.  Used by dict_contains(), index(),
// get(), and set().
//
// For now this does a linear search.
// TODO:
// - hash functions, and linear probing.
// - resizing based on load factor
//   - which requires rehashing (re-insert all items)
// - Special case to intern Str* when it's hashed?  How?
//   - Should we have wrappers like:
//   - V GetAndIntern<V>(D, &string_key)
//   - SetAndIntern<V>(D, &string_key, value)
//   This will enable duplicate copies of the string to be garbage collected
template <typename K, typename V>
int Dict<K, V>::position_of_key(K key) {
  auto self = this;
  StackRoots _roots({&self});

  for (int i = 0; i < self->capacity_; ++i) {
    int special = self->entry_->items_[i];  // NOT an index now
    if (special == kDeletedEntry) {
      continue;  // keep searching
    }
    if (special == kEmptyEntry) {
      return -1;  // not found
    }
    if (keys_equal(self->keys_->items_[i], key)) {
      return i;
    }
  }
  return -1;  // table is completely full?  Does this happen?
}

// Four overloads for dict_set()!  TODO: Is there a nicer way to do this?
// e.g. Dict<int, int>
template <typename K, typename V>
void dict_set(Dict<K, V>* self, K key, V val) {
  StackRoots _roots({&self});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

// e.g. Dict<Str*, int>
template <typename K, typename V>
void dict_set(Dict<K*, V>* self, K* key, V val) {
  StackRoots _roots({&self, &key});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

// e.g. Dict<int, Str*>
template <typename K, typename V>
void dict_set(Dict<K, V*>* self, K key, V* val) {
  StackRoots _roots({&self, &val});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

// e.g. Dict<Str*, Str*>
template <typename K, typename V>
void dict_set(Dict<K*, V*>* self, K* key, V* val) {
  StackRoots _roots({&self, &key, &val});

  self->reserve(self->len_ + 1);
  self->keys_->items_[self->len_] = key;
  self->values_->items_[self->len_] = val;

  self->entry_->items_[self->len_] = 0;  // new special value

  ++self->len_;
}

template <typename K, typename V>
void Dict<K, V>::set(K key, V val) {
  auto self = this;
  StackRoots _roots({&self});  // May not need this here?

  int pos = self->position_of_key(key);
  if (pos == -1) {             // new pair
    dict_set(self, key, val);  // ALLOCATES
  } else {
    self->values_->items_[pos] = val;
  }
}

template <typename K, typename V>
inline int len(const Dict<K, V>* d) {
  return d->len_;
}

template <typename K, typename V>
void dict_remove(Dict<K, V>* haystack, K needle) {
  int pos = haystack->position_of_key(needle);
  if (pos == -1) {
    return;
  }
  haystack->entry_->items_[pos] = kDeletedEntry;
  // Zero out for GC.  These could be nullptr or 0
  haystack->keys_->items_[pos] = 0;
  haystack->values_->items_[pos] = 0;
  haystack->len_--;
}

template <typename K, typename V>
void Dict<K, V>::remove(K key) {
  dict_remove(this, key);
}

#endif
