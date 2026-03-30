import argparse
import os
import random
from pathlib import Path
import signal
import sys

from satfuzzer.SatFuzzer import SatFuzzer


def signal_handler(sig, frame):
    print("\nFuzzer interrupted. Exiting gracefully...")

    # # Kill all processes in our process group
    # try:
    #     os.killpg(os.getpgid(0), signal.SIGTERM)
    # except ProcessLookupError:
    #     pass  # No processes left to kill
 
    sys.exit(0)


# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)


def main():
    parser = argparse.ArgumentParser(description="SAT Solver Fuzzer", prog="./fuzz-sat")
    parser.add_argument("sut_path", help="Path to the root directory of the fuzzer")
    parser.add_argument("inputs_path", help="Path to a directory containing well-formed CNF files")
    parser.add_argument("seed", type=int, help="Random seed for reproducibility")

    args = parser.parse_args()

    sut_path = Path(args.sut_path)
    inputs_path = Path(args.inputs_path)
    seed = args.seed

    if not (sut_path / "runsat.sh").is_file():
        print("runsat.sh not found in sut_path", file=sys.stderr)
        sys.exit(1)

    if not any(inputs_path.glob("*.cnf")):
        print("No .cnf files found in inputs_path", file=sys.stderr)
        sys.exit(1)

    random.seed(seed)

    fuzzer = SatFuzzer(sut_path, inputs_path)

    # Make sure child processes are in their own process group
    # os.setpgrp()

    fuzzer.run()

    print("Fuzzing completed.")


if __name__ == "__main__":
    main()
