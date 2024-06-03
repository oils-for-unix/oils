/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file ExplainTree.h
 *
 * Classes for storing a derivation tree
 *
 ***********************************************************************/

#pragma once

#include "souffle/utility/ContainerUtil.h"
#include "souffle/utility/StringUtil.h"
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace souffle {

class ScreenBuffer {
public:
    // constructor
    ScreenBuffer(uint32_t w, uint32_t h) : width(w), height(h), buffer(nullptr) {
        assert(width > 0 && height > 0 && "wrong dimensions");
        buffer = new char[width * height];
        memset(buffer, ' ', width * height);
    }

    ~ScreenBuffer() {
        delete[] buffer;
    }

    // write into screen buffer at a specific location
    void write(uint32_t x, uint32_t y, const std::string& s) {
        assert(x < width && "wrong x dimension");
        assert(y < height && "wrong y dimension");
        assert(x + s.length() <= width && "string too long");
        for (std::size_t i = 0; i < s.length(); i++) {
            buffer[y * width + x + i] = s[i];
        }
    }

    std::string getString() {
        std::stringstream ss;
        print(ss);
        return ss.str();
    }

    // print screen buffer
    void print(std::ostream& os) {
        if (height > 0 && width > 0) {
            for (int i = height - 1; i >= 0; i--) {
                for (std::size_t j = 0; j < width; j++) {
                    os << buffer[width * i + j];
                }
                os << std::endl;
            }
        }
    }

private:
    uint32_t width;   // width of the screen buffer
    uint32_t height;  // height of the screen buffer
    char* buffer;     // screen contents
};

/***
 * Abstract Class for a Proof Tree Node
 *
 */
class TreeNode {
public:
    TreeNode(std::string t = "") : txt(std::move(t)) {}
    virtual ~TreeNode() = default;

    // get width
    uint32_t getWidth() const {
        return width;
    }

    // get height
    uint32_t getHeight() const {
        return height;
    }

    // place the node
    virtual void place(uint32_t xpos, uint32_t ypos) = 0;

    // render node in screen buffer
    virtual void render(ScreenBuffer& s) = 0;

    std::size_t getSize() {
        return size;
    }

    void setSize(std::size_t s) {
        size = s;
    }

    virtual void printJSON(std::ostream& os, int pos) = 0;

protected:
    std::string txt;      // text of tree node
    uint32_t width = 0;   // width of node (including sub-trees)
    uint32_t height = 0;  // height of node (including sub-trees)
    int xpos = 0;         // x-position of text
    int ypos = 0;         // y-position of text
    uint32_t size = 0;
};

/***
 * Concrete class
 */
class InnerNode : public TreeNode {
public:
    InnerNode(const std::string& nodeText = "", std::string label = "")
            : TreeNode(nodeText), label(std::move(label)) {}

    // add child to node
    void add_child(Own<TreeNode> child) {
        children.push_back(std::move(child));
    }

    // place node and its sub-trees
    void place(uint32_t x, uint32_t y) override {
        // there must exist at least one kid
        assert(!children.empty() && "no children");

        // set x/y pos
        xpos = x;
        ypos = y;

        height = 0;

        // compute size of bounding box
        for (const Own<TreeNode>& k : children) {
            k->place(x, y + 2);
            x += k->getWidth() + 1;
            width += k->getWidth() + 1;
            height = std::max(height, k->getHeight());
        }
        height += 2;

        // text of inner node is longer than all its sub-trees
        if (width < txt.length()) {
            width = txt.length();
        }
    };

    // render node text and separator line
    void render(ScreenBuffer& s) override {
        s.write(xpos + (width - txt.length()) / 2, ypos, txt);
        for (const Own<TreeNode>& k : children) {
            k->render(s);
        }
        std::string separator(width - label.length(), '-');
        separator += label;
        s.write(xpos, ypos + 1, separator);
    }

    // print JSON
    void printJSON(std::ostream& os, int pos) override {
        std::string tab(pos, '\t');
        os << tab << R"({ "premises": ")" << stringify(txt) << "\",\n";
        os << tab << R"(  "rule-number": ")" << label << "\",\n";
        os << tab << "  \"children\": [\n";
        bool first = true;
        for (const Own<TreeNode>& k : children) {
            if (first) {
                first = false;
            } else {
                os << ",\n";
            }
            k->printJSON(os, pos + 1);
        }
        os << tab << "]\n";
        os << tab << "}";
    }

private:
    VecOwn<TreeNode> children;
    std::string label;
};

/***
 * Concrete class for leafs
 */
class LeafNode : public TreeNode {
public:
    LeafNode(const std::string& t = "") : TreeNode(t) {
        setSize(1);
    }

    // place leaf node
    void place(uint32_t x, uint32_t y) override {
        xpos = x;
        ypos = y;
        width = txt.length();
        height = 1;
    }

    // render text of leaf node
    void render(ScreenBuffer& s) override {
        s.write(xpos, ypos, txt);
    }

    // print JSON
    void printJSON(std::ostream& os, int pos) override {
        std::string tab(pos, '\t');
        os << tab << R"({ "axiom": ")" << stringify(txt) << "\"}";
    }
};

}  // end of namespace souffle
