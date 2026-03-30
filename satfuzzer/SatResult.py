from typing import NamedTuple


class FileLocation(NamedTuple):
    file: str
    line: int


class UndefinedBehaviour(NamedTuple):
    description: str
    location: FileLocation


class CoverageResult(NamedTuple):
    location: FileLocation
    bucket_index: int
