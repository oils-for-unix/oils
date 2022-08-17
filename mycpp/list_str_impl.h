


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

#if 0
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
#else

int find_next_occurance_of(const char *haystack, int starting_index, int end_index, const char needle)
{
  int result = end_index;
  for (int i = starting_index; i < end_index; ++i)
  {
    if (haystack[i] == needle)
    {
      result = i;
      break;
    }
  }
  return result;
}

List<Str*>* Str::split(Str* sep) {
  assert(len(sep) == 1);  // we can only split one char
  char sep_char = sep->data_[0];

  auto self = this;
  List<Str*> *result = nullptr;

  StackRoots _roots({&self, &result});

  if (len(self) == 0) {
    // weird case consistent with Python: ''.split(':') == ['']
    return NewList<Str*>({kEmptyString});
  }

  result = NewList<Str*>({});

  int n = len(self);
  int pos = 0;
  int end = n;

  while (true) {
    // NOTE(Jesse): Perfect use case for cursor
    int new_pos = find_next_occurance_of(self->data_, pos, end, sep_char);
    assert(new_pos >= pos);
    assert(new_pos <= end);

    if (new_pos == end) {
      result->append(StrFromC(self->data_+pos, end - pos));  // rest of the string
      break;
    }

    int new_len = new_pos - pos;
    result->append(StrFromC(self->data_+pos, new_len));
    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(kEmptyString);
      break;
    }
  }

  return result;
}
#endif
