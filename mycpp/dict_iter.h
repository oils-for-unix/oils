#ifndef DICT_ITER_H
#define DICT_ITER_H

template <class K, class V>
class DictIter {
 public:
  explicit DictIter(Dict<K, V>* D) : D_(D), pos_(ValidPosAfter(0)) {
  }
  void Next() {
    pos_ = ValidPosAfter(pos_ + 1);
  }
  bool Done() {
    return pos_ == -1;
  }
  K Key() {
    return D_->keys_->items_[pos_];
  }
  V Value() {
    return D_->values_->items_[pos_];
  }

 private:
  int ValidPosAfter(int pos) {
    // Returns the position of a valid entry at or after index i_.  Or -1 if
    // there isn't one.  Advances i_ too.
    while (true) {
      if (pos >= D_->capacity_) {
        return -1;
      }
      int index = D_->entry_->items_[pos];
      if (index == kDeletedEntry) {
        ++pos;
        continue;  // increment again
      }
      if (index == kEmptyEntry) {
        return -1;
      }
      break;
    }
    return pos;
  }

  Dict<K, V>* D_;
  int pos_;
};

#endif  // GC_BUILTINS_H
