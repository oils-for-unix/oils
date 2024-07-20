/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2017, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file Explain.h
 *
 * Provenance interface for Souffle; works for compiler and interpreter
 *
 ***********************************************************************/

#pragma once

#include "souffle/provenance/ExplainProvenance.h"
#include "souffle/provenance/ExplainProvenanceImpl.h"
#include "souffle/provenance/ExplainTree.h"
#include <algorithm>
#include <csignal>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <regex>
#include <string>
#include <utility>
#include <vector>
#include <unistd.h>

#ifdef USE_NCURSES
#include <ncurses.h>
#endif

#define MAX_TREE_HEIGHT 500
#define MAX_TREE_WIDTH 500

namespace souffle {
class SouffleProgram;

class ExplainConfig {
public:
    /* Deleted copy constructor */
    ExplainConfig(const ExplainConfig&) = delete;

    /* Deleted assignment operator */
    ExplainConfig& operator=(const ExplainConfig&) = delete;

    /* Obtain the global ExplainConfiguration */
    static ExplainConfig& getExplainConfig() {
        static ExplainConfig config;
        return config;
    }

    /* Configuration variables */
    Own<std::ostream> outputStream = nullptr;
    bool json = false;
    int depthLimit = 4;

private:
    ExplainConfig() = default;
};

class Explain {
public:
    ExplainProvenance& prov;

    Explain(ExplainProvenance& prov) : prov(prov) {}
    ~Explain() = default;

    /* Process a command, a return value of true indicates to continue, returning false indicates to break (if
     * the command is q/exit) */
    bool processCommand(std::string& commandLine) {
        std::vector<std::string> command = split(commandLine, ' ', 1);

        if (command.empty()) {
            return true;
        }

        if (command[0] == "setdepth") {
            if (command.size() != 2) {
                printError("Usage: setdepth <depth>\n");
                return true;
            }
            try {
                ExplainConfig::getExplainConfig().depthLimit = std::stoi(command[1]);
            } catch (std::exception& e) {
                printError("<" + command[1] + "> is not a valid depth\n");
                return true;
            }
            printInfo("Depth is now " + std::to_string(ExplainConfig::getExplainConfig().depthLimit) + "\n");
        } else if (command[0] == "explain") {
            std::pair<std::string, std::vector<std::string>> query;
            if (command.size() != 2) {
                printError("Usage: explain relation_name(\"<string element1>\", <number element2>, ...)\n");
                return true;
            }
            query = parseTuple(command[1]);
            printTree(prov.explain(query.first, query.second, ExplainConfig::getExplainConfig().depthLimit));
        } else if (command[0] == "subproof") {
            std::pair<std::string, std::vector<std::string>> query;
            int label = -1;
            if (command.size() <= 1) {
                printError("Usage: subproof relation_name(<label>)\n");
                return true;
            }
            query = parseTuple(command[1]);
            label = std::stoi(query.second[0]);
            printTree(prov.explainSubproof(query.first, label, ExplainConfig::getExplainConfig().depthLimit));
        } else if (command[0] == "explainnegation") {
            std::pair<std::string, std::vector<std::string>> query;
            if (command.size() != 2) {
                printError(
                        "Usage: explainnegation relation_name(\"<string element1>\", <number element2>, "
                        "...)\n");
                return true;
            }
            query = parseTuple(command[1]);

            // a counter for the rule numbers
            std::size_t i = 1;
            std::string rules;

            // if there are no rules, then this must be an EDB relation
            if (prov.getRules(query.first).size() == 0) {
                printInfo("The tuple would be an input fact!\n");
                return true;
            }

            for (auto rule : prov.getRules(query.first)) {
                rules += std::to_string(i) + ": ";
                rules += rule;
                rules += "\n\n";
                i++;
            }
            printInfo(rules);

            printPrompt("Pick a rule number: ");

            std::string ruleNum = getInput();
            auto variables = prov.explainNegationGetVariables(query.first, query.second, std::stoi(ruleNum));

            // @ and @non_matching are special sentinel values returned by ExplainProvenance
            if (variables.size() == 1 && variables[0] == "@") {
                printInfo("The tuple exists, cannot explain negation of it!\n");
                return true;
            } else if (variables.size() == 1 && variables[0] == "@non_matching") {
                printInfo("The variable bindings don't match, cannot explain!\n");
                return true;
            } else if (variables.size() == 1 && variables[0] == "@fact") {
                printInfo("The rule is a fact!\n");
                return true;
            }

            std::map<std::string, std::string> varValues;
            for (auto var : variables) {
                printPrompt("Pick a value for " + var + ": ");
                varValues[var] = getInput();
            }

            printTree(prov.explainNegation(query.first, std::stoi(ruleNum), query.second, varValues));
        } else if (command[0] == "rule" && command.size() == 2) {
            auto query = split(command[1], ' ');
            if (query.size() != 2) {
                printError("Usage: rule <relation name> <rule number>\n");
                return true;
            }
            try {
                printInfo(prov.getRule(query[0], std::stoi(query[1])) + "\n");
            } catch (std::exception& e) {
                printError("Usage: rule <relation name> <rule number>\n");
            }
        } else if (command[0] == "measure") {
            try {
                printInfo(prov.measureRelation(command[1]));
            } catch (std::exception& e) {
                printError("Usage: measure <relation name>\n");
            }
        } else if (command[0] == "output") {
            if (command.size() == 2) {
                // assign a new filestream, the old one is deleted by unique_ptr
                ExplainConfig::getExplainConfig().outputStream = mk<std::ofstream>(command[1]);
            } else if (command.size() == 1) {
                ExplainConfig::getExplainConfig().outputStream = nullptr;
            } else {
                printError("Usage: output  [<filename>]\n");
            }
        } else if (command[0] == "format") {
            if (command.size() == 2 && command[1] == "json") {
                ExplainConfig::getExplainConfig().json = true;
            } else if (command.size() == 2 && command[1] == "proof") {
                ExplainConfig::getExplainConfig().json = false;
            } else {
                printError("Usage: format <json|proof>\n");
            }
        } else if (command[0] == "exit" || command[0] == "q" || command[0] == "quit") {
            // close file stream so that output is actually written to file
            printPrompt("Exiting explain\n");
            return false;
        } else if (command[0] == "query") {
            // if there is no given relations, return directly
            if (command.size() != 2) {
                printError(
                        "Usage: query <relation1>(<element1>, <element2>, ...), "
                        "<relation2>(<element1>, <element2>, ...), ...\n");
                return true;
            }
            // vector relations stores relation name, args pair parsed by parseQueryTuple()
            std::vector<std::pair<std::string, std::vector<std::string>>> relations;
            // regex for relation string
            std::regex relationRegex(
                    "([a-zA-Z0-9_.-]*)[[:blank:]]*\\(([[:blank:]]*([0-9]+|\"[^\"]*\"|[a-zA-Z_][a-zA-Z_0-9]*)("
                    "[[:blank:]]*,[[:blank:]]*(["
                    "0-"
                    "9]+|\"[^\"]*\"|[a-zA-Z_][a-zA-Z_0-9]*))*)?\\)",
                    std::regex_constants::extended);
            std::smatch relationMatcher;
            std::string relationStr = command[1];
            // use relationRegex to match each relation string and call parseQueryTuple() to parse the
            // relation name and arguments
            while (std::regex_search(relationStr, relationMatcher, relationRegex)) {
                relations.push_back(parseQueryTuple(relationMatcher[0]));

                // check return value for parseQueryTuple, return if relation name is empty string or tuple
                // arguments is empty
                if (relations.back().first.size() == 0 || relations.back().second.size() == 0) {
                    printError(
                            "Usage: query <relation1>(<element1>, <element2>, ...), "
                            "<relation2>(<element1>, <element2>, ...), ...\n");
                    return true;
                }
                relationStr = relationMatcher.suffix().str();
            }

            // is no valid relation can be identified, return directly
            if (relations.size() == 0) {
                printError(
                        "Usage: query <relation1>(<element1>, <element2>, ...), "
                        "<relation2>(<element1>, <element2>, ...), ...\n");
                return true;
            }

            // call queryProcess function to process query
            prov.queryProcess(relations);
        } else {
            printError(
                    "\n----------\n"
                    "Commands:\n"
                    "----------\n"
                    "setdepth <depth>: Set a limit for printed derivation tree height\n"
                    "explain <relation>(<element1>, <element2>, ...): Prints derivation tree\n"
                    "explainnegation <relation>(<element1>, <element2>, ...): Enters an interactive\n"
                    "    interface where the non-existence of a tuple can be explained\n"
                    "subproof <relation>(<label>): Prints derivation tree for a subproof, label is\n"
                    "    generated if a derivation tree exceeds height limit\n"
                    "rule <relation name> <rule number>: Prints a rule\n"
                    "output <filename>: Write output into a file, or provide empty filename to\n"
                    "    disable output\n"
                    "format <json|proof>: switch format between json and proof-trees\n"
                    "query <relation1>(<element1>, <element2>, ...), <relation2>(<element1>, <element2>), "
                    "... :\n"
                    "check existence of constant tuples or find solutions for parameterised tuples\n"
                    "for parameterised query, use semicolon to find next solution and dot to break from "
                    "query\n"
                    "exit: Exits this interface\n\n");
        }

        return true;
    }

    /* The main explain call */
    virtual void explain() = 0;

private:
    /* Get input */
    virtual std::string getInput() = 0;

    /* Print a command prompt, disabled for non-terminal outputs */
    virtual void printPrompt(const std::string& prompt) = 0;

    /* Print a tree */
    virtual void printTree(Own<TreeNode> tree) = 0;

    /* Print any other information, disabled for non-terminal outputs */
    virtual void printInfo(const std::string& info) = 0;

    /* Print an error, such as a wrong command */
    virtual void printError(const std::string& error) = 0;

    /**
     * Parse tuple, split into relation name and values
     * @param str The string to parse, should be something like "R(x1, x2, x3, ...)"
     */
    std::pair<std::string, std::vector<std::string>> parseTuple(const std::string& str) {
        std::string relName;
        std::vector<std::string> args;

        // regex for matching tuples
        // values matches numbers or strings enclosed in quotation marks
        std::regex relationRegex(
                "([a-zA-Z0-9_.-]*)[[:blank:]]*\\(([[:blank:]]*([0-9]+|\"[^\"]*\")([[:blank:]]*,[[:blank:]]*(["
                "0-"
                "9]+|\"[^\"]*\"))*)?\\)",
                std::regex_constants::extended);
        std::smatch relMatch;

        // first check that format matches correctly
        // and extract relation name
        if (!std::regex_match(str, relMatch, relationRegex) || relMatch.size() < 3) {
            return std::make_pair(relName, args);
        }

        // set relation name
        relName = relMatch[1];

        // extract each argument
        std::string argsList = relMatch[2];
        std::smatch argsMatcher;
        std::regex argRegex(R"([0-9]+|"[^"]*")", std::regex_constants::extended);

        while (std::regex_search(argsList, argsMatcher, argRegex)) {
            // match the start of the arguments
            std::string currentArg = argsMatcher[0];
            args.push_back(currentArg);

            // use the rest of the arguments
            argsList = argsMatcher.suffix().str();
        }

        return std::make_pair(relName, args);
    }

    /**
     * Parse tuple for query, split into relation name and args, additionally allow varaible as argument in
     * relation tuple
     * @param str The string to parse, should be in form "R(x1, x2, x3, ...)"
     */
    std::pair<std::string, std::vector<std::string>> parseQueryTuple(const std::string& str) {
        std::string relName;
        std::vector<std::string> args;
        // regex for matching tuples
        // values matches numbers or strings enclosed in quotation marks
        std::regex relationRegex(
                "([a-zA-Z0-9_.-]*)[[:blank:]]*\\(([[:blank:]]*([0-9]+|\"[^\"]*\"|[a-zA-Z_][a-zA-Z_0-9]*)([[:"
                "blank:]]*,[[:blank:]]*(["
                "0-"
                "9]+|\"[^\"]*\"|[a-zA-Z_][a-zA-Z_0-9]*))*)?\\)",
                std::regex_constants::extended);
        std::smatch relMatch;

        // if the given string does not match relationRegex, return a pair of empty string and empty vector
        if (!std::regex_match(str, relMatch, relationRegex) || relMatch.size() < 3) {
            return std::make_pair(relName, args);
        }

        // set relation name
        relName = relMatch[1];

        // extract each argument
        std::string argsList = relMatch[2];
        std::smatch argsMatcher;
        std::regex argRegex(R"([0-9]+|"[^"]*"|[a-zA-Z_][a-zA-Z_0-9]*)", std::regex_constants::extended);
        while (std::regex_search(argsList, argsMatcher, argRegex)) {
            // match the start of the arguments
            std::string currentArg = argsMatcher[0];
            args.push_back(currentArg);

            // use the rest of the arguments
            argsList = argsMatcher.suffix().str();
        }

        return std::make_pair(relName, args);
    }
};

class ExplainConsole : public Explain {
public:
    explicit ExplainConsole(ExplainProvenance& provenance) : Explain(provenance) {}

    /* The main explain call */
    void explain() override {
        printPrompt("Explain is invoked.\n");

        while (true) {
            printPrompt("Enter command > ");
            std::string line = getInput();
            // a return value of false indicates that an exit/q command has been processed
            if (!processCommand(line)) {
                break;
            }
        }
    }

private:
    /* Get input */
    std::string getInput() override {
        std::string line;

        if (!getline(std::cin, line)) {
            // if EOF has been reached, quit
            line = "q";
        }

        return line;
    }

    /* Print a command prompt, disabled for non-terminal outputs */
    void printPrompt(const std::string& prompt) override {
        if (isatty(fileno(stdin)) == 0) {
            return;
        }
        std::cout << prompt;
    }

    /* Print a tree */
    void printTree(Own<TreeNode> tree) override {
        if (!tree) {
            return;
        }

        // handle a file ostream output
        std::ostream* output;
        if (ExplainConfig::getExplainConfig().outputStream == nullptr) {
            output = &std::cout;
        } else {
            output = ExplainConfig::getExplainConfig().outputStream.get();
        }

        if (!ExplainConfig::getExplainConfig().json) {
            tree->place(0, 0);
            ScreenBuffer screenBuffer(tree->getWidth(), tree->getHeight());
            tree->render(screenBuffer);
            *output << screenBuffer.getString();
        } else {
            *output << "{ \"proof\":\n";
            tree->printJSON(*output, 1);
            *output << ",";
            prov.printRulesJSON(*output);
            *output << "}\n";
        }
    }

    /* Print any other information, disabled for non-terminal outputs */
    void printInfo(const std::string& info) override {
        if (isatty(fileno(stdin)) == 0) {
            return;
        }
        std::cout << info;
    }

    /* Print an error, such as a wrong command */
    void printError(const std::string& error) override {
        std::cout << error;
    }
};

#ifdef USE_NCURSES
class ExplainNcurses : public Explain {
public:
    explicit ExplainNcurses(ExplainProvenance& provenance) : Explain(provenance) {}

    /* The main explain call */
    void explain() override {
        if (ExplainConfig::getExplainConfig().outputStream == nullptr) {
            initialiseWindow();
            std::signal(SIGWINCH, nullptr);
        }

        printPrompt("Explain is invoked.\n");

        while (true) {
            clearDisplay();
            printPrompt("Enter command > ");
            std::string line = getInput();

            // a return value of false indicates that an exit/q command has been processed
            if (!processCommand(line)) {
                break;
            }

            // refresh treePad and allow scrolling
            prefresh(treePad, 0, 0, 0, 0, maxy - 3, maxx - 1);
            scrollTree(maxx, maxy);
        }

        // clean up
        endwin();
    }

private:
    WINDOW* treePad = nullptr;
    WINDOW* queryWindow = nullptr;
    int maxx, maxy;

    /* Get input */
    std::string getInput() override {
        char buf[100];

        curs_set(1);
        echo();

        // get next command
        wgetnstr(queryWindow, buf, 100);
        noecho();
        curs_set(0);
        std::string line = buf;

        return line;
    }

    /* Print a command prompt, disabled for non-terminal outputs */
    void printPrompt(const std::string& prompt) override {
        if (!isatty(fileno(stdin))) {
            return;
        }
        werase(queryWindow);
        wrefresh(queryWindow);
        mvwprintw(queryWindow, 1, 0, "%s", prompt.c_str());
    }

    /* Print a tree */
    void printTree(Own<TreeNode> tree) override {
        if (!tree) {
            return;
        }

        if (!ExplainConfig::getExplainConfig().json) {
            tree->place(0, 0);
            ScreenBuffer screenBuffer(tree->getWidth(), tree->getHeight());
            tree->render(screenBuffer);
            wprintw(treePad, "%s", screenBuffer.getString().c_str());
        } else {
            if (ExplainConfig::getExplainConfig().outputStream == nullptr) {
                std::stringstream ss;
                ss << "{ \"proof\":\n";
                tree->printJSON(ss, 1);
                ss << ",";
                prov.printRulesJSON(ss);
                ss << "}\n";

                wprintw(treePad, "%s", ss.str().c_str());
            } else {
                std::ostream* output = ExplainConfig::getExplainConfig().outputStream.get();
                *output << "{ \"proof\":\n";
                tree->printJSON(*output, 1);
                *output << ",";
                prov.printRulesJSON(*output);
                *output << "}\n";
            }
        }
    }

    /* Print any other information, disabled for non-terminal outputs */
    void printInfo(const std::string& info) override {
        if (!isatty(fileno(stdin))) {
            return;
        }
        wprintw(treePad, "%s", info.c_str());
        prefresh(treePad, 0, 0, 0, 0, maxy - 3, maxx - 1);
    }

    /* Print an error, such as a wrong command */
    void printError(const std::string& error) override {
        wprintw(treePad, "%s", error.c_str());
        prefresh(treePad, 0, 0, 0, 0, maxy - 3, maxx - 1);
    }

    /* Initialise ncurses command prompt window */
    WINDOW* makeQueryWindow() {
        WINDOW* queryWindow = newwin(3, maxx, maxy - 2, 0);
        wrefresh(queryWindow);
        return queryWindow;
    }

    /* Initialise ncurses window */
    void initialiseWindow() {
        initscr();

        // get size of window
        getmaxyx(stdscr, maxy, maxx);

        // create windows for query and tree display
        queryWindow = makeQueryWindow();
        treePad = newpad(MAX_TREE_HEIGHT, MAX_TREE_WIDTH);

        keypad(treePad, true);
    }

    /* Allow scrolling of provenance tree */
    void scrollTree(int maxx, int maxy) {
        int x = 0;
        int y = 0;

        while (true) {
            int ch = wgetch(treePad);

            if (ch == KEY_LEFT) {
                if (x > 2) x -= 3;
            } else if (ch == KEY_RIGHT) {
                if (x < MAX_TREE_WIDTH - 3) x += 3;
            } else if (ch == KEY_UP) {
                if (y > 0) y -= 1;
            } else if (ch == KEY_DOWN) {
                if (y < MAX_TREE_HEIGHT - 1) y += 1;
            } else {
                ungetch(ch);
                break;
            }

            prefresh(treePad, y, x, 0, 0, maxy - 3, maxx - 1);
        }
    }

    /* Clear the tree display */
    void clearDisplay() {
        // reset tree display on each loop
        werase(treePad);
        prefresh(treePad, 0, 0, 0, 0, maxy - 3, maxx - 1);
    }
};
#endif

inline void explain(SouffleProgram& prog, bool ncurses) {
    ExplainProvenanceImpl prov(prog);

    if (ncurses) {
#ifdef USE_NCURSES
        ExplainNcurses exp(prov);
        exp.explain();
#else
        std::cout << "The ncurses-based interface is not enabled\n";
#endif
    } else {
        ExplainConsole exp(prov);
        exp.explain();
    }
}

// this is necessary because ncurses.h defines TRUE and FALSE macros, and they otherwise clash with our parser
#ifdef USE_NCURSES
#undef TRUE
#undef FALSE
#endif

}  // end of namespace souffle
