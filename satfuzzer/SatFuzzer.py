from bisect import bisect_left
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from collections import deque

from satfuzzer.SatInput import SatInput, StructuredSatInput
from satfuzzer.SatMutator import mutate
from satfuzzer.SatResult import CoverageResult, FileLocation, UndefinedBehaviour


type Count = int
type BucketIndex = int


class SatFuzzer:
    def __init__(self, sut_path: Path, inputs_path: Path):
        self.sut_path = sut_path
        self.inputs_path = inputs_path

        self.input_queue: deque[SatInput] = deque() 

        # {(file, line, error)}
        self.seen_errors: set[UndefinedBehaviour] = set()

        self.BUCKET_GROWTH_RATIO = 1.6
        self.MAX_COVERAGE_COUNT = 1_000_000_000
        self.exponential_buckets: list[int] = self.create_buckets()

        # {(file, line, bucket_index)}
        self.seen_lines: set[CoverageResult] = set()

        self.MAX_INTERESTING_INPUTS = 20
        self.interesting_inputs: list[tuple[SatInput, set[UndefinedBehaviour]]] = []

        self.fuzzed_tests_directory = Path("fuzzed-tests")
        self.outputs_directory = Path("fuzzed-outputs")

        self.temp_file = "temp.cnf"

        self.TIMEOUT_SECONDS = 2
        self.COVERAGE_TIMEOUT_SECONDS = 5

        self.SAVE_INTERVAL = 2  # How often to save interesting inputs

        self.new_ub_count = 0
        self.new_coverage_count = 0
        self.nothing_new_count = 0

    def create_buckets(self) -> list[int]:
        assert self.BUCKET_GROWTH_RATIO > 1.0, "Bucket growth ratio must be greater than 1.0"

        bounds: list[int] = [0] + sorted({int(self.BUCKET_GROWTH_RATIO**n) for n in range(100)})
        last_index = None
        for i, n in enumerate(bounds):
            if n > self.MAX_COVERAGE_COUNT:
                last_index = i
                break
        if last_index is not None:
            bounds = bounds[: last_index + 1]

        return bounds

    def convert_to_buckets(self, coverage: dict[FileLocation, Count]) -> set[CoverageResult]:
        coverage_buckets: set[CoverageResult] = set()

        for loc, count in coverage.items():
            bucket = bisect_left(self.exponential_buckets, count)
            coverage_buckets.add(CoverageResult(location=loc, bucket_index=bucket))

        return coverage_buckets

    def run(self):
        # Load initial inputs into the queue
        self.load_inputs()

        # Remove the directories if it exists and recreate it
        for dir_path in [self.fuzzed_tests_directory, self.outputs_directory]:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    print(f"Failed to remove directory {dir_path}: {e}", file=sys.stderr)
                    sys.exit(1)
            dir_path.mkdir()

        print("Starting fuzzing loop...")
        iteration = 0
        while iteration := iteration + 1:
            print(f"--- Fuzzing iteration {iteration} ---")
            
            print(f"Current queue size: {len(self.input_queue)}")

            # Changed from self.input_queue._queue to self.input_queue
            semantically_valid = sum(1 for i in self.input_queue if isinstance(i, StructuredSatInput) and i.is_semantically_valid) 
            semantically_invalid = sum(1 for i in self.input_queue if isinstance(i, StructuredSatInput) and not i.is_semantically_valid)
            syntactically_invalid = len(self.input_queue) - semantically_valid - semantically_invalid
            print(f"  Semantically valid inputs:    {semantically_valid}")
            print(f"  Semantically invalid inputs:  {semantically_invalid}")
            print(f"  Syntactically invalid inputs: {syntactically_invalid}")

            if not self.input_queue:
                print("No more inputs to process. Exiting fuzzer.")
                break

            current_input = self.input_queue.popleft()

            self.new_ub_count = 0
            self.new_coverage_count = 0
            self.nothing_new_count = 0

            ms = mutate(current_input)
            print(f"Generated mutated inputs.")
            for mutated_input in ms:
                self.run_with_input(mutated_input)

            print(f"  New ubs this iteration:      {self.new_ub_count}")
            print(f"  New coverage this iteration: {self.new_coverage_count}")
            print(f"  Nothing new this iteration:  {self.nothing_new_count}")

    def run_with_input(self, mutated_input: SatInput):
        # print("Running SUT with mutated input...")
        result = self.run_sut(mutated_input)

        # print("SUT run completed. Analyzing coverage...")
        coverage = self.get_coverage()

        coverage_buckets = self.convert_to_buckets(coverage)

        # print("Processing result...")
        ubs = self.get_undefined_behaviours(result)

        if ubs and len(self.interesting_inputs) < self.MAX_INTERESTING_INPUTS:
            self.interesting_inputs.append((mutated_input, ubs))
            self.write_interesting_input(len(self.interesting_inputs) - 1)

        new_ubs: set[UndefinedBehaviour] = set()
        for ub in ubs:
            if ub not in self.seen_errors:
                self.seen_errors.add(ub)
                new_ubs.add(ub)

        if new_ubs:
            self.new_ub_count += 1
        else:
            # evaluate coverage
            new_coverage: set[CoverageResult] = set()
            for cr in coverage_buckets:
                if cr not in self.seen_lines:
                    self.seen_lines.add(cr)
                    new_coverage.add(cr)
            if new_coverage:
                self.new_coverage_count += 1
            else:
                self.nothing_new_count += 1
                return

        # TODO consider coverage here too

        self.input_queue.append(mutated_input) 

        if new_ubs and len(self.interesting_inputs) >= self.MAX_INTERESTING_INPUTS:
            self.eviction(mutated_input, ubs)

    def run_sut(self, sat_input: SatInput) -> str:
        # Clear previous coverage files
        for file in self.sut_path.glob("*.gcda"):
            try:
                file.unlink()
            except Exception as e:
                print(f"Failed to remove coverage file {file}: {e}", file=sys.stderr)
                sys.exit(1)

        try:
            with open(self.temp_file, "w") as f:
                f.write(sat_input.to_cnf())

            result = subprocess.run(
                [str(self.sut_path / "runsat.sh"), self.temp_file],
                capture_output=True,
                text=False,  # Handle binary output
                timeout=self.TIMEOUT_SECONDS,
            )
            return result.stderr.decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired as e:
            print(f"Process timed out")
            return e.stderr.decode("utf-8", errors="replace") if e.stderr else ""

    def load_inputs(self):
        for cnf_file in self.inputs_path.glob("*.cnf"):
            with open(cnf_file, "r") as f:
                lines = f.readlines()

            num_vars = 0
            clauses: list[list[int | str]] = []

            for line in lines:
                line = line.split()
                match line:
                    case ["p", "cnf", num_vars_str, _]:
                        num_vars = int(num_vars_str)
                    case ["#", _]:
                        # Comment line, skip
                        continue
                    case clause:
                        clause_lits = [int(lit) if lit.lstrip("-").isdigit() else lit for lit in clause if lit != "0"]
                        clauses.append(clause_lits)

            # assume well-formed eh?
            sat_input = StructuredSatInput(num_vars=num_vars, clauses=clauses, is_semantically_valid=True)
            self.input_queue.append(sat_input)

    def get_undefined_behaviours(self, stderr: str) -> set[UndefinedBehaviour]:
        if not stderr:
            return set()

        ubs = set()

        # Match only the initial error lines from UBSan, ignore addresses and diagnostic notes
        ubsan_re = re.compile(
            r"(?P<file>[\w\.\-/]+):(?P<line>\d+):(?P<col>\d+):\s*runtime error:\s*(?P<message>.+)", re.MULTILINE
        )
        # re.compile(r"^([^:]+):(\d+):(\d+): runtime error: ([^0-9A-Fa-fx]+)(?:0x[\da-f]+ )?", re.MULTILINE)

        # SUMMARY: AddressSanitizer: heap-buffer-overflow /home/user/Programming/Fuzzing_16/solvers/solver1/formula.c:141 in init_formula_from_file
        asan_re = re.compile(
            r"SUMMARY: AddressSanitizer: (?P<message>[^/]+) (?:[^/]+/)*(?P<file>[^/:]+):(?P<line>\d+) in \w+",
            re.MULTILINE,
        )

        ubsan_matches = ubsan_re.finditer(stderr)
        for match in ubsan_matches:
            m = match.groupdict()
            line = int(m["line"])

            message = m["message"].strip()

            # Replace any hex numbers with '?' in the error message
            message = re.sub(r"0x[0-9a-fA-F]+", "?", m["message"])
            loc = FileLocation(file=m["file"], line=line)
            ub = UndefinedBehaviour(description=message, location=loc)
            ubs.add(ub)

        asan_matches = asan_re.finditer(stderr)
        for match in asan_matches:
            m = match.groupdict()
            line = int(m["line"])

            # Replace any hex numbers with '?' in the error message
            message = re.sub(r"0x[0-9a-fA-F]+", "?", m["message"])
            loc = FileLocation(file=m["file"], line=line)
            ub = UndefinedBehaviour(description=message, location=loc)
            ubs.add(ub)

        return ubs

    def eviction(self, new_input: SatInput, new_ubs: set[UndefinedBehaviour]):
        # Evaluate current interesting inputs
        existing_errors: set[str] = set()
        existing_locations: set[FileLocation] = set()
        existing_total_errors = 0
        for _, ubs in self.interesting_inputs:
            for ub in ubs:
                existing_errors.add(ub.description)
                existing_locations.add(ub.location)
            existing_total_errors += len(ubs)

        # In order of priority: number of unique errors, number of unique locations, total number of errors
        score = (len(existing_errors), len(existing_locations), existing_total_errors)

        # Try to replace each existing interesting input, see if score improves
        index_to_evict = None
        max_score = score

        for index in range(len(self.interesting_inputs)):
            new_errors: set[str] = {ub.description for ub in new_ubs}
            new_locations: set[FileLocation] = {ub.location for ub in new_ubs}
            new_total_errors = len(new_ubs)
            for i, (_, ubs) in enumerate(self.interesting_inputs):
                if index == i:
                    continue
                for ub in ubs:
                    new_errors.add(ub.description)
                    new_locations.add(ub.location)
                new_total_errors += len(ubs)

            new_score = (len(new_errors), len(new_locations), new_total_errors)
            if new_score > max_score:
                max_score = new_score
                index_to_evict = index

        if index_to_evict is not None:
            print(f"Evicted interesting input {index_to_evict} for a better one.")
            self.interesting_inputs[index_to_evict] = (new_input, new_ubs)
            self.write_interesting_input(index_to_evict)

    def get_coverage(self) -> dict[FileLocation, Count]:
        try:
            for file in self.sut_path.glob("*.c"):
                subprocess.run(
                    ["gcov", "-bjf", file.name],
                    cwd=self.sut_path,
                    capture_output=True,
                    text=True,
                    timeout=self.COVERAGE_TIMEOUT_SECONDS,
                    check=True,
                )
            for file in self.sut_path.glob("*.gcov.json.gz"):
                subprocess.run(
                    ["gzip", "-df", file.name],
                    cwd=self.sut_path,
                    capture_output=True,
                    text=True,
                    timeout=self.COVERAGE_TIMEOUT_SECONDS,
                    check=True,
                )
        except subprocess.TimeoutExpired:
            print(f"gcov timed out, exiting", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(
                f"gcov failed with return code {e.returncode}, exiting:\n{e.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

        coverage: dict[FileLocation, int] = {}
        for json_file in self.sut_path.glob("*.gcov.json"):
            with open(json_file) as f:
                data = json.load(f)

            file_data = data["files"][0]  # Take first (and only) file
            name = Path(file_data["file"]).name

            for line in file_data["lines"]:
                count = line.get("count", 0)
                if count == 0 and not line.get("unexecuted_block", False):
                    continue  # Line cannot be run

                loc = FileLocation(file=name, line=line["line_number"])
                coverage[loc] = count

        return coverage

    def write_interesting_input(self, index: int):
        print(f"Writing interesting input {index} to disk...")

        sat_input, ubs = self.interesting_inputs[index]
        input_filename = self.fuzzed_tests_directory / f"interesting_input_{index}.cnf"
        with open(input_filename, "w") as f:
            f.write(sat_input.to_cnf())

        ubs_filename = self.outputs_directory / f"interesting_input_{index}_errors.txt"
        with open(ubs_filename, "w") as f:
            for ub in ubs:
                f.write(f"{ub.location.file}:{ub.location.line}: {ub.description}\n")
