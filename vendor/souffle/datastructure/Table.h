/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2013, 2015, Oracle and/or its affiliates. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Table.h
 *
 * An implementation of a generic Table storing a position-fixed collection
 * of objects in main memory.
 *
 ***********************************************************************/

#pragma once

#include <iosfwd>
#include <iterator>

namespace souffle {

template <typename T, unsigned blockSize = 4096>
class Table {
    struct Block {
        Block* next;
        std::size_t used = 0;
        T data[blockSize];

        Block() : next(nullptr) {}

        bool isFull() const {
            return used == blockSize;
        }

        const T& append(const T& element) {
            const T& res = data[used];
            data[used] = element;
            used++;
            return res;
        }
    };

    Block* head;
    Block* tail;

    std::size_t count = 0;

public:
    class iterator {
        Block* block;
        unsigned pos;

    public:
        using iterator_category = std::forward_iterator_tag;
        using value_type = T;
        using difference_type = void;
        using pointer = T*;
        using reference = T&;

        iterator(Block* block = nullptr, unsigned pos = 0) : block(block), pos(pos) {}

        iterator(const iterator&) = default;
        iterator(iterator&&) = default;
        iterator& operator=(const iterator&) = default;

        // the equality operator as required by the iterator concept
        bool operator==(const iterator& other) const {
            return (block == nullptr && other.block == nullptr) || (block == other.block && pos == other.pos);
        }

        // the not-equality operator as required by the iterator concept
        bool operator!=(const iterator& other) const {
            return !(*this == other);
        }

        // the deref operator as required by the iterator concept
        const T& operator*() const {
            return block->data[pos];
        }

        // the increment operator as required by the iterator concept
        iterator& operator++() {
            // move on in block
            if (++pos < block->used) {
                return *this;
            }
            // or to next block
            block = block->next;
            pos = 0;
            return *this;
        }
    };

    Table() : head(nullptr), tail(nullptr) {}

    ~Table() {
        clear();
    }

    bool empty() const {
        return (!head);
    }

    std::size_t size() const {
        return count;
    }

    const T& insert(const T& element) {
        // check whether the head is initialized
        if (!head) {
            head = new Block();
            tail = head;
        }

        // check whether tail is full
        if (tail->isFull()) {
            tail->next = new Block();
            tail = tail->next;
        }

        // increment counter
        count++;

        // add another element
        return tail->append(element);
    }

    iterator begin() const {
        return iterator(head);
    }

    iterator end() const {
        return iterator();
    }

    void clear() {
        while (head != nullptr) {
            auto cur = head;
            head = head->next;
            delete cur;
        }
        count = 0;
        head = nullptr;
        tail = nullptr;
    }
};

}  // end namespace souffle
