from typing import Iterable
from satfuzzer.SatInput import SatInput, UnstructuredSatInput, StructuredSatInput
import random
import copy
import string

NUMBER_OF_MUTATIONS = 50

SEMANTICALLY_VALID_RATIO = 0.7
SEMANTICALLY_INVALID_RATIO = 0.28


MUTATE_CLAUSE_PROBABILITY = 0.5
MUTATE_LITERAL_PROBABILITY = 0.5
NEGATE_VS_CHANGE_PROBABILITY = 0.5
ZERO_LITERAL_CLAUSE_PROBABILITY = 0.01

NUM_VARS_RANGE = (0.2, 5.0)
NUM_CLAUSES_RANGE = (0.75, 1.25)
NUM_LITERALS_RANGE = (0.2, 2.0)

# Syntactic mutation probabilities
SYNTACTIC_MUTATION_PROBABILITY = 0.5
STRING_LITERAL_PROBABILITY = 0.3
OUT_OF_BOUNDS_PROBABILITY = 0.3
MALFORMED_CLAUSE_PROBABILITY = 0.2
NO_TERMINATOR_PROBABILITY = 0.05


def mutate(sat_input: SatInput) -> Iterable[SatInput]:
    mutated_sat_inputs = []
    if isinstance(sat_input, StructuredSatInput):
        # If semantically valid, generate both semantically valid and invalid mutations
        if sat_input.is_semantically_valid:
            for _ in range(int(NUMBER_OF_MUTATIONS * SEMANTICALLY_VALID_RATIO)):
                sat_input_copy = sat_input.copy()
                mutate_sat_input_semantically(sat_input_copy)
                mutated_sat_inputs.append(sat_input_copy)
            for _ in range(int(NUMBER_OF_MUTATIONS * SEMANTICALLY_INVALID_RATIO)):
                sat_input_copy = sat_input.copy()
                mutate_sat_input_syntactically(sat_input_copy)
                mutated_sat_inputs.append(sat_input_copy)
        else :# If semantically invalid, only generate syntactic mutations
            for _ in range(NUMBER_OF_MUTATIONS):
                sat_input_copy = sat_input.copy()
                mutate_sat_input_syntactically(sat_input_copy)
                mutated_sat_inputs.append(sat_input_copy)

        # Also generate unstructured mutations
        unstructured_copy = UnstructuredSatInput(list(sat_input.to_cnf()))
        mutate_sat_input_unstructured(unstructured_copy)
        mutated_sat_inputs.append(unstructured_copy)
    elif isinstance(sat_input, UnstructuredSatInput):
        sat_input_copy = sat_input.copy()
        mutate_sat_input_unstructured(sat_input_copy)
        mutated_sat_inputs.append(sat_input_copy)
    else:
        assert False, "unreachable"

    random.shuffle(mutated_sat_inputs)
    return mutated_sat_inputs

possible_characters = string.ascii_letters + string.digits + string.punctuation + " \n\t"


def mutate_sat_input_unstructured(sat_input: UnstructuredSatInput):
    num_to_mutate = int(len(sat_input.content) * 0.05)
    indices_to_mutate = random.sample(range(len(sat_input.content)), k=num_to_mutate)
    chars_to_swap = random.choices(possible_characters, k=num_to_mutate)

    for i, c in zip(indices_to_mutate, chars_to_swap):
        sat_input.content[i] = c


def mutate_sat_input_syntactically(sat_input: StructuredSatInput):
    # 1. change some literals to strings
    # 2. change some literals to out-of-bounds values
    # 3. change some clauses to be just singleton string
    # 4. change some clauses to have no terminator

    sat_input.is_semantically_valid = False

    # Choose which syntactic mutations to apply (at least one)
    mutations = []
    if random.random() < SYNTACTIC_MUTATION_PROBABILITY:
        mutations.append("string_literals")
    if random.random() < SYNTACTIC_MUTATION_PROBABILITY:
        mutations.append("out_of_bounds")
    if random.random() < SYNTACTIC_MUTATION_PROBABILITY:
        mutations.append("malformed_clauses")
    if random.random() < SYNTACTIC_MUTATION_PROBABILITY:
        mutations.append("no_terminator")

    # Ensure at least one mutation is applied
    if not mutations:
        mutations = [random.choice(["string_literals", "out_of_bounds", "malformed_clauses", "no_terminator"])]

    num_to_malform = int(len(sat_input.clauses) * MUTATE_CLAUSE_PROBABILITY)
    indices_to_malform = random.sample(range(len(sat_input.clauses)), k=num_to_malform)

    # Mutate clauses
    for i in indices_to_malform:
        clause = sat_input.clauses[i]
        # Apply malformed clause mutation
        if "malformed_clauses" in mutations:
            sat_input.clauses[i] = generate_malformed_clause()
            continue  # Skip literal mutations for malformed clauses

        # Mutate literals in this clause syntactically
        mutate_clause_syntactically(sat_input.num_vars, clause, mutations)

    if "no_terminator" not in mutations: return

    num_to_remove_terminator = int(len(sat_input.clauses) * NO_TERMINATOR_PROBABILITY)
    indices_to_remove_terminator = random.sample(range(len(sat_input.clauses)), k=num_to_remove_terminator)

    for i in indices_to_remove_terminator:
        # Apply no terminator mutation independently
        sat_input.unterminated_clauses.add(i)


def generate_malformed_clause() -> list[str | int]:
    """Generate a malformed clause for syntactic testing."""
    malformed_choices: list[list[str | int]] = [
        ["p", "cnf"],  # Header-like clause
        [""],  # Empty string
        ["%", "comment"],  # Comment-like clause
        ["#"],  # Comment symbol
    ]
    return random.choice(malformed_choices)


def mutate_clause_syntactically(num_vars: int, clause: list[int | str], mutations: list[str]):
    """Mutate literals in a clause syntactically (strings or out-of-bounds values)."""
    num_to_mutate = int(len(clause) * MUTATE_LITERAL_PROBABILITY)
    indices_to_mutate = random.sample(range(len(clause)), k=num_to_mutate)
    for i in indices_to_mutate:
        lit = clause[i]
        if isinstance(lit, int):
            clause[i] = mutate_literal_syntactically(num_vars, lit, mutations)


def mutate_literal_syntactically(num_vars: int, literal: int, mutations: list[str]) -> int | str:
    """Mutate a literal to be either a string or out-of-bounds value."""
    # Apply string literal mutation
    if "string_literals" in mutations and random.random() < 0.5:
        return generate_string_literal()
    # Apply out-of-bounds mutation
    elif "out_of_bounds" in mutations:
        return generate_out_of_bounds_literal(num_vars)
    return literal


def generate_string_literal() -> str:
    """Generate an invalid string literal."""
    string_choices = ["x", "var", "true", "false", "", "null", "NaN", "inf"]
    return random.choice(string_choices)


def generate_out_of_bounds_literal(num_vars: int) -> int:
    """Generate an out-of-bounds literal value."""
    out_of_bounds_choices = [
        num_vars + random.randint(1, 100),  # Too large positive
        -(num_vars + random.randint(1, 100)),  # Too large negative
        2**15 - 1, # Max short
        -2**15, # Min short
        2**31 - 1, # Max int
        -2**31, # Min int
        2**63 - 1, # Max long
        -2**63, # Min long
    ]
    return random.choice(out_of_bounds_choices) if random.random() < 0.995 else 0  # Occasionally return zero as out-of-bounds


def mutate_sat_input_semantically(sat_input: StructuredSatInput):
    # 1. let's mutate number of vars first
    # 2. then we'll mutate number of clauses
    # 3. then we'll add/delete clauses accordingly to match the new number of clauses
    # 4. then we'll mutate the clauses themselves

    # 1. let's mutate number of vars first
    num_vars = sat_input.num_vars
    new_num_vars = int(random.uniform(*NUM_VARS_RANGE) * num_vars)
    sat_input.num_vars = new_num_vars

    # 2. then we'll mutate number of clauses
    num_clauses = len(sat_input.clauses)
    new_num_clauses = int(random.uniform(*NUM_CLAUSES_RANGE) * num_clauses)

    # 3. then we'll add/delete clauses accordingly to match the new number of clauses
    n = new_num_clauses - num_clauses
    if n > 0:
        indices_to_copy = random.choices(range(len(sat_input.clauses)), k=n)
        for idx in indices_to_copy:
            clause_copy = copy.copy(sat_input.clauses[idx])
            sat_input.clauses.append(clause_copy)
    for _ in range(num_clauses - new_num_clauses):
        sat_input.clauses.pop()

    # 4. Clamp in a single pass
    for clause in sat_input.clauses:
        # First, clamp any existing literals that are now out of bounds
        for i, literal in enumerate(clause):
            if isinstance(literal, int) and abs(literal) > new_num_vars:
                clause[i] = new_num_vars if literal > 0 else -new_num_vars

    num_to_mutate = int(len(sat_input.clauses) * MUTATE_CLAUSE_PROBABILITY)
    indices_to_mutate = random.sample(range(len(sat_input.clauses)), k=num_to_mutate)
    for i in indices_to_mutate:
        mutate_clause(new_num_vars, sat_input.clauses[i])


def mutate_clause(num_vars: int, clause: list[int | str]) -> list[int | str]:
    # 1. we'll mutate the number of literals in the clause
    # 2. then we'll iterate through each literal. 50% chance of leaving the literal as is, and 50% chance of changing it
    # 3. change means:
    #  - 50% chance of negating the literal
    #  - 50% chance of changing the literal to a different one
    #  - these are independent probability executions, not mutually exclusive

    new_num_literals = int(random.uniform(*NUM_LITERALS_RANGE) * len(clause))
    for _ in range(new_num_literals - len(clause)):  # for adding new literals
        clause.append(generate_literal(num_vars))
    for _ in range(len(clause) - new_num_literals):  # for removing literals
        clause.pop()

    num_to_mutate = int(len(clause) * MUTATE_LITERAL_PROBABILITY)
    indices_to_mutate = random.sample(range(len(clause)), k=num_to_mutate)

    for i in indices_to_mutate:
        clause[i] = mutate_literal(num_vars, clause[i])

    return clause


def generate_literal(num_vars: int) -> int | str:
    return random.randint(-num_vars, num_vars)


def mutate_literal(num_vars: int, literal: int | str) -> int | str:
    should_negate = random.random() < NEGATE_VS_CHANGE_PROBABILITY
    if should_negate and isinstance(literal, int):
        literal = -literal
        return literal
    else:
        literal = generate_literal(num_vars)
    return literal
