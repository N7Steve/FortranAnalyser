"""Serializable public results; unknown metrics are null, never fabricated zeroes."""

from dataclasses import asdict, dataclass, field
from typing import Literal

Status = Literal["ok", "partial", "failed", "skipped"]


@dataclass
class Finding:
    rule: str
    path: str
    line: int
    severity: Literal["info", "warning", "error"]
    message: str


@dataclass
class Scope:
    name: str
    kind: str
    line: int
    end_line: int
    qualified_name: str
    implicit_none: bool | None
    declarations: int = 0
    declared_entities: int = 0
    loops: int = 0
    max_loop_depth: int = 0
    calls: int = 0


@dataclass
class Metrics:
    physical_lines: int
    declarations: int
    declared_entities: int
    functions: int
    subroutines: int
    modules: int
    programs: int
    loops: int
    max_loop_depth: int
    calls: int


@dataclass
class FileResult:
    path: str
    status: Status
    source_form: str
    physical_lines: int | None = None
    metrics: Metrics | None = None
    scopes: list[Scope] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ProjectResult:
    schema_version: str
    rules_version: str
    parser: str
    files: list[FileResult]
    summary: dict

    def to_dict(self) -> dict:
        return asdict(self)
