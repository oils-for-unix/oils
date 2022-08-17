
Str* Str::join(List<Str*>* items) {
  auto self = this;
  StackRoots _roots({&self, &items});

  int length = 0;

  int num_parts = len(items);
  if (num_parts == 0) {  // " ".join([]) == ""
    return kEmptyString;
  }
  for (int i = 0; i < num_parts; ++i) {
    length += len(items->index_(i));
  }
  // add length of all the separators
  int len_ = len(self);
  length += len_ * (num_parts - 1);

  char* result = static_cast<char*>(malloc(length + 1));
  char* p_result = result;  // advances through

  for (int i = 0; i < num_parts; ++i) {
    // log("i %d", i);
    if (i != 0 && len_) {             // optimize common case of ''.join()
      memcpy(p_result, data_, len_);  // copy the separator
      p_result += len_;
      // log("len_ %d", len_);
    }

    int n = len(items->index_(i));
    // log("n: %d", n);
    memcpy(p_result, items->index_(i)->data_, n);  // copy the list item
    p_result += n;
  }

  result[length] = '\0';  // NUL terminator

  return CopyBufferIntoNewStr(result, length);
}

List<Str*>* Str::split(Str* sep) {
  auto self = this;
  List<Str*>* result = nullptr;
  char* place = nullptr;
  StackRoots _roots({&self, &sep, &result, &place});

  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  int length = len(this);
  if (length == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return NewList<Str*>(std::initializer_list<Str*>{kEmptyString});
  }

  // Find breaks first so we can allocate the right number of strings ALL AT
  // ONCE. We want to avoid invalidating self->data_.
  int num_bytes = 0;
  int prev_pos = -1;
  std::vector<int> breaks;
  breaks.push_back(-1);  // beginning of first part

  for (int i = 0; i < length; ++i) {
    if (data_[i] == sep_char) {
      breaks.push_back(i);
      int part_len = i - prev_pos - 1;
      if (part_len > 0) {  // only non-empty parts
        num_bytes += aligned(kStrHeaderSize + part_len + 1);
      }
      prev_pos = i;
    }
  }
  breaks.push_back(length);  // end of last part

  if (length) {
    int last_part_len = length - prev_pos - 1;
    if (last_part_len > 0) {
      num_bytes += aligned(kStrHeaderSize + last_part_len + 1);
    }
  }

  result = NewList<Str*>(nullptr, breaks.size() - 1);  // reserve enough space

  place = reinterpret_cast<char*>(gHeap.Allocate(num_bytes));
  int n = breaks.size();
  for (int i = 1; i < n; ++i) {
    int prev_pos = breaks[i - 1];
    int part_len = breaks[i] - prev_pos - 1;
    if (part_len > 0) {
      // like AllocStr(), but IN PLACE
      int obj_len = kStrHeaderSize + part_len + 1;  // NUL terminator
      Str* part = new (place) Str();                // placement new
      part->SetObjLen(obj_len);                     // So the GC can copy it
      memcpy(part->data_, self->data_ + prev_pos + 1, part_len);
      result->set(i - 1, part);
      place += aligned(obj_len);
    } else {
      result->set(i - 1, kEmptyString);  // save some space
    }
  }

  return result;
}
