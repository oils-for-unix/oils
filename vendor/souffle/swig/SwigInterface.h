/*
 * Souffle - A Datalog Compiler
 * Copyright (c) 2019, The Souffle Developers. All rights reserved
 * Licensed under the Universal Permissive License v 1.0 as shown at:
 * - https://opensource.org/licenses/UPL
 * - <souffle root>/licenses/SOUFFLE-UPL.txt
 */

/************************************************************************
 *
 * @file SwigInterface.h
 *
 * Header file for SWIG to invoke functions in souffle::SouffleProgram
 *
 ***********************************************************************/

#pragma once

#include "souffle/SouffleInterface.h"
#include <iostream>
#include <string>

/**
 * Abstract base class for generated Datalog programs
 */
class SWIGSouffleProgram {
    /**
     * pointer to SouffleProgram to invoke functions from SouffleInterface.h
     */
    souffle::SouffleProgram* program;

public:
    SWIGSouffleProgram(souffle::SouffleProgram* program) : program(program) {}

    virtual ~SWIGSouffleProgram() {
        delete program;
    }

    /**
     * Calls the corresponding method souffle::SouffleProgram::run in SouffleInterface.h
     */
    void run() {
        program->run();
    }

    /**
     * Calls the corresponding method souffle::SouffleProgram::runAll in SouffleInterface.h
     */
    void runAll(const std::string& inputDirectory, const std::string& outputDirectory) {
        program->runAll(inputDirectory, outputDirectory);
    }

    /**
     * Calls the corresponding method souffle::SouffleProgram::loadAll in SouffleInterface.h
     */
    void loadAll(const std::string& inputDirectory) {
        program->loadAll(inputDirectory);
    }

    /**
     * Calls the corresponding method souffle::SouffleProgram::printAll in SouffleInterface.h
     */
    void printAll(const std::string& outputDirectory) {
        program->printAll(outputDirectory);
    }

    /**
     * Calls the corresponding method souffle::SouffleProgram::dumpInputs in SouffleInterface.h
     */
    void dumpInputs() {
        program->dumpInputs();
    }

    /**
     * Calls the corresponding method souffle::SouffleProgram::dumpOutputs in SouffleInterface.h
     */
    void dumpOutputs() {
        program->dumpOutputs();
    }
};

/**
 * Creates an instance of a SWIG souffle::SouffleProgram that can be called within a program of a supported
 * language for the SWIG option specified in main.cpp. This enables the program to use this instance and call
 * the supported souffle::SouffleProgram methods.
 * @param name Name of the datalog file/ instance to be created
 */
SWIGSouffleProgram* newInstance(const std::string& name) {
    auto* prog = souffle::ProgramFactory::newInstance(name);
    return new SWIGSouffleProgram(prog);
}
