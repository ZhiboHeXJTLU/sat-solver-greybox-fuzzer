# Provided solvers

This directory contains 3 SAT solvers made by students in previous years that will be used to exercise your fuzzer implementations.
In principle you could ignore these and implement a dumb fuzzing scheme.
Nevertheless, we **strongly** encourage you to implement to implement some form of feedback fuzzing.
To simplify your fuzzers, the solvers are implemented in C and the source directory is structured as follows:

- `sat.c` The main file for the SAT solver
- `*.c`, `.h` Some number of source files in the root directory needed to build the solver
- `Makefile` The Makefile builds the solver using the `make ub` command. The resulting executable is named `./sat`. The resulting executable is instrumented using ASan and UBSan and produces coverage information in gcov format. However you should not run this executable directly. You can also remove build artifacts and `gcov` files using the `clean` target.
- `runsat.sh` This wrapper script allows you to run the solver built using the provided Makefile. This exists because ASan and UBSan expect certain environment variables to contain various configuration options. You don't have to worry about this when using this script.

## You should not modify anything in this directory.

Doing so would not help you since this is the exact setup used to assess your fuzzers.

