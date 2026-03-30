from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class SatInput(ABC):
    """Base class for SAT input representations."""

    @abstractmethod
    def to_cnf(self) -> str:
        """Convert the SAT input to CNF format string."""
        pass

    @abstractmethod
    def copy(self) -> "SatInput":
        """Create a deep copy of the SAT input."""
        pass


@dataclass
class UnstructuredSatInput(SatInput):
    """Unstructured representation of a SAT input as raw text."""

    content: list[str]

    def to_cnf(self) -> str:
        return "".join(self.content)

    def copy(self) -> "UnstructuredSatInput":
        new_content = self.content[:]
        return UnstructuredSatInput(new_content)



@dataclass
class StructuredSatInput(SatInput):
    """Structured representation of a SAT input with parsed components."""

    num_vars: int
    clauses: list[list[int | str]]
    is_semantically_valid: bool
    unterminated_clauses: set[int] = field(default_factory=set)  # Indices of clauses that have terminators

    def to_cnf(self) -> str:
        lines = [f"p cnf {self.num_vars} {len(self.clauses)}"]
        for i, clause in enumerate(self.clauses):
            clause_line = " ".join(str(lit) for lit in clause) + " 0" if i not in self.unterminated_clauses else ""
            lines.append(clause_line)
        return "\n".join(lines)

    def copy(self) -> 'StructuredSatInput':
        """Creates a copy of the object much faster than deepcopy."""
        # Create a new, empty instance to avoid re-running __init__
        new_copy = self.__class__.__new__(self.__class__)
        
        # Copy attributes directly
        new_copy.num_vars = self.num_vars
        new_copy.is_semantically_valid = self.is_semantically_valid
        
        # Efficiently copy the list of lists and the set
        new_copy.clauses = [clause[:] for clause in self.clauses]
        new_copy.unterminated_clauses = self.unterminated_clauses.copy()

        return new_copy
