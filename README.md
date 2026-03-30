# 70024 Software Reliability Fuzzer Coursework

This is the base repository for your fuzzer coursework.
You should write your code here.

## The fuzzer interface

In this coursework, you will implement a DIMACS fuzzer.
DIMACS is a format describing a boolean formula in conjunctive normal form (CNF).
Some information about this format can be found at the following links:

- <https://fairmut3x.wordpress.com/2011/07/29/cnf-conjunctive-normal-form-dimacs-format-explained/>
- <http://www.domagoj-babic.com/uploads/ResearchProjects/Spear/dimacs-cnf.pdf>

The aim of the fuzzer is to find bugs in SAT solvers that were built in C by some of your peers in previous years.
Your fuzzer will take as input one of these SAT solvers.
We also refer to the SAT solver that your fuzzer is applied to as SUT which stands for *system under test*.
To further test your fuzzer, note that you can (and are encouraged to) also use a production level SAT solver (such as MiniSAT <http://github.com/niklasso/minisat>) as SUT.

The interface of the resulting fuzzer should be `fuzz-sat /path/to/SUT /path/to/inputs seed` where:

- `/path/to/SUT` refers to the source directory of the SUT containing the built solver (with gcov coverage information, ASan, and UBSan enabled) and the `runsat.sh` script that needs to be used to run the solver. The `runsat.sh` script expects a single command line argument, the path to a file containing the input formula, and prints out whether the formula was satisfiable, optionally a model, and the error reports of ASan and UBSan if any issues were detected.
- `/path/to/inputs` refers to a directory containing a non-empty set of well-formed DIMACS files.
- `seed` is an integer that you should use to initialize a random number generator if you need one.

## The build script

In the top-level directory of this repository, you will find the `build.sh` script.
This script is used to build your fuzzer and you should use it to install any dependencies your fuzzer might need and to compile your fuzzer's source code if necessary.
After the script runs we expect to find the `fuzz-sat` executable described previously in the top-level directory of this repository.

You can use the build script to download compilers, interpreters, runtimes, software libraries, and to compile your fuzzer's source code.
The only requirement is that the script and resulting executable can run on a standard lab-machine with network access.
However if you plan to use uncommon languages or libraries, we ask that you notify us ahead of time so we can decide whether someone on the team would be able to mark your submission (we might ask you to use a different language if we can not find anyone that can mark your work). 
If you program in an interpreted language using an interpreter already installed on lab-machines, the build script does not need to do anything.

## The fuzzer output

Your fuzzer should create a directory `fuzzed-tests` in the **current working directory** that contains at **most 20** test cases that are known to trigger an undefined behavior in the SUT.
In principle your fuzzer should operate in an infinite loop as follows:

1. Generate an input.
2. Run the SUT (using the provided `runsat.sh` script) on the input, killing the SUT after a timeout of your choice.
3. If an undefined behavior was triggered, consider saving the test case in `fuzzed-tests`
4. Go back to step 1.

It is up to you how you handle step 1.
You could take a generation-based approach, making inputs from scratch, or a mutation-based approach, modifying existing or previously-generated inputs. 
You could employ dumb fuzzing, generating or mutating without reference to the DIMACS format, or a form of smart fuzzing, generating DIMACS or DIMACS-like inputs, or mutating existing inputs in a manner that partially or wholly respects the DIMACS format.
It is also up to you whether you try to maximize coverage in a blind fashion, by simply generating a diverse range of inputs that are likely to give high coverage, or whether you do so in a feedback-directed fashion, using coverage information to guide input production.
For the latter, it is up to you to learn how to use coverage information provided by gcov.

It is important to use a timeout in step 2 since the SUT might enter an infinite loop.
The challenge is to find a timeout that allows you to get a high fuzzing rate while still running the SUT long enough to achieve good coverage.

In step 3, to determine whether undefined behavior as occurred, you will need to examine the sanitizers' output.
You might also want to implement an eviction policy that takes SUT coverage and undefined behavior uniqueness into account.
If you generate more than 20 tests we will select 20 of them at random.

You are free to employ parallelism inside your fuzzer, as your implementation will be evaluated on a multi-core system.
This is usually a good way of increasing the fuzzing rate.

## Evaluation

When we evaluate your fuzzer, we will run it for 30 minutes per-SUT on a range of SUTs.
For each SUT we will score you based on:

- The cumulative coverage achieved **during fuzzing**. You do not need to track this, our testing infrastructure will do this for you, but please ensure you don't delete the files generated by `gcov`.
- The diversity of bug inducing tests that you save in `fuzzed-tests`. If you generate more than 20, we will select 20 at random.
