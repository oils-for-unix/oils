
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

int find_next(const char *haystack, int starting_index, int end_index, const char needle)
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

Str *NewStrFromHeapStr(Str *src, int new_len, int start_index = 0)
{
  StackRoots _roots({&src});

  Str *result = AllocStr(new_len);
  assert( (start_index+new_len) <= len(src));
  memcpy(result->data_, src->data_+start_index, new_len);

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
    int new_pos = find_next(self->data_, pos, end, sep_char);
    assert(new_pos >= pos);
    assert(new_pos <= end);

    if (new_pos == end) {
      Str *to_push = NewStrFromHeapStr(self, end-pos, pos);
      result->append(to_push); //StrFromC(self->data_+pos, end - pos));  // rest of the string
      break;
    }

    int new_len = new_pos - pos;
    Str *to_push = NewStrFromHeapStr(self, new_len, pos);
    result->append(to_push);

    pos = new_pos + 1;
    if (pos >= end) {  // separator was at end of string
      result->append(kEmptyString);
      break;
    }
  }

  return result;
}
