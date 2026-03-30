# 70024 Software Reliability SAT Solver Greybox Fuzzer Coursework

An AFL-inspired greybox mutation-based fuzzer for DIMACS CNF SAT solvers, developed for the 70024 Software Reliability coursework at Imperial College London.

This project combines grammar-aware mutation, sanitizer feedback, and gcov-based coverage guidance to discover diverse bug-inducing inputs for SAT solvers.

## Overview

The goal of this project is to test SAT solvers by automatically generating and mutating DIMACS-format CNF inputs, then using runtime feedback to identify interesting behaviors.

The fuzzer is designed as a smart greybox mutation-based fuzzer. Instead of relying only on random byte-level corruption, it exploits the structure of the DIMACS format and uses:

- **ASan / UBSan** to identify undefined behaviors
- **gcov** to track coverage and execution diversity
- **queue-based scheduling** inspired by AFL
- **eviction logic** to retain diverse bug-inducing tests

## Key Features

- AFL-inspired queue-based greybox fuzzing workflow
- Grammar-aware mutation for DIMACS CNF SAT inputs
- Three mutation modes:
  - **Structured mutation** for semantically valid transformations
  - **Syntactic mutation** for parser robustness testing
  - **Unstructured mutation** for random raw-byte corruption
- Feedback from:
  - AddressSanitizer (ASan)
  - UndefinedBehaviorSanitizer (UBSan)
  - gcov coverage files
- Coverage-guided input selection with exponential bucketing
- Eviction policy to retain up to 20 diverse bug-inducing test cases
- Profiling-driven optimization using `cProfile`

## Mutation Strategy

The fuzzer uses three disjoint mutation categories.

### 1. Structured Mutation

These mutations preserve DIMACS validity while changing the semantics of the formula. Examples include:

- adding or removing clauses
- negating literals
- replacing literals
- scaling the number of clauses or variables

This allows the fuzzer to explore deeper solver logic while maintaining well-formed CNF structure.

### 2. Syntactic Mutation

These mutations intentionally break DIMACS syntax to test parser robustness. Examples include:

- replacing literals with malformed strings such as `x` or `NaN`
- using out-of-bound variable indices
- removing clause terminators
- injecting malformed clauses

These cases are useful for triggering sanitizer feedback in parser-related code paths.

### 3. Unstructured Mutation

These mutations perform random byte-level corruption without respecting input grammar. This provides a complementary “dumb fuzzing” mode for exploring unexpected error paths.

## Feedback and Interestingness

Inputs are considered interesting if they:

- trigger new undefined behaviors, or
- reach new coverage patterns

To capture more nuanced execution differences, coverage information is summarized using **exponential buckets**, rather than storing only exact raw counts.

Interesting inputs are re-added to the queue for further mutation.

## Eviction Policy

The fuzzer keeps up to **20 bug-inducing test cases** in `fuzzed-tests/`.

When the set is full, a new candidate is considered based on whether it improves result diversity. The diversity score takes into account:

1. number of unique error types
2. number of unique source locations
3. total number of errors triggered

This helps preserve a compact but diverse set of bug-inducing tests.

## Performance Optimization

During development, profiling with Python `cProfile` revealed that semantic mutation and repeated random calls inside loops were major bottlenecks.

To improve throughput:

- mutation indices were precomputed instead of repeatedly sampling inside loops
- clause generation was optimized by duplicating existing clauses instead of generating many new ones from scratch

These changes significantly improved fuzzing performance and increased the number of unique bugs found during a run.

## Project Structure

```text
.
├── build.sh
├── fuzz-sat
├── src/
├── inputs/
├── fuzzed-tests/
├── docs/
│   └── report.pdf
└── README.md
```

## How to Build
./build.sh

After running the build script, the fuzz-sat executable should be available in the repository root.

## How to Run
```bash
./fuzz-sat /path/to/SUT /path/to/inputs 123
```

Where:

/path/to/SUT is the SAT solver source directory containing the instrumented solver and runsat.sh
/path/to/inputs is a directory with well-formed DIMACS CNF seed files
123 is the random seed
Output

The fuzzer creates a directory named fuzzed-tests/ in the current working directory and stores up to 20 interesting bug-inducing test cases there.

## Evaluation

The fuzzer was evaluated by running it on multiple SAT solvers and observing:

throughput
newly discovered undefined behaviors
new coverage over time
diversity of saved bug-inducing tests

Short 10-minute evaluation runs were used during development for fast iteration, while the coursework setting evaluated fuzzers over longer runs.

## Coursework Context

This project was developed as part of the 70024 Software Reliability coursework at Imperial College London.

The coursework task was to implement a DIMACS fuzzer for SAT solvers built in C, with feedback collected via gcov, ASan, and UBSan.

## Report

A short report describing the design, optimizations, and evaluation of the fuzzer is available in:

```text
sat-solver-greybox-fuzzer
/report.pdf
```
## Notes

This repository is intended as a compact project showcase of implementation and testing-tool design experience.

## License

MIT License