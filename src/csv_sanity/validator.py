"""Validate CSV structure without modifying the input or retaining its rows."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    line: int | None = None


@dataclass
class Report:
    path: str
    data_rows: int = 0
    columns: int | None = None
    issue_count: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.issue_count == 0

    def to_dict(self) -> dict:
        return {**asdict(self), "valid": self.valid}


def validate(
    path: str | Path,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
    header: bool = True,
    max_issues: int = 50,
) -> Report:
    """Check header names, row widths, decoding, and CSV parsing.

    Empty physical records are skipped. Issue line numbers identify the final
    physical line of a record, including records with quoted newlines. All
    detectable issues are counted, but only max_issues details are retained.
    """
    if len(delimiter) != 1 or delimiter in "\r\n\0\"":
        raise ValueError("delimiter must be one character other than a newline, NUL, or quote")
    if max_issues < 1:
        raise ValueError("max_issues must be at least 1")

    report = Report(path=str(path))

    def add_issue(code: str, message: str, line: int | None = None) -> None:
        report.issue_count += 1
        if len(report.issues) < max_issues:
            report.issues.append(Issue(code, message, line))

    reader = None
    try:
        with Path(path).open("r", encoding=encoding, newline="") as source:
            reader = csv.reader(source, delimiter=delimiter, strict=True)
            for row in reader:
                if not row:
                    continue
                if report.columns is None:
                    report.columns = len(row)
                    if header:
                        seen = set()
                        for column, name in enumerate(row, start=1):
                            normalized = name.strip()
                            if not normalized:
                                add_issue("blank_header", f"Column {column} has a blank header.", reader.line_num)
                            elif normalized in seen:
                                add_issue("duplicate_header", f"Column {column} repeats a header name.", reader.line_num)
                            seen.add(normalized)
                        continue
                report.data_rows += 1
                if len(row) != report.columns:
                    add_issue(
                        "row_width",
                        f"Expected {report.columns} fields, found {len(row)}.",
                        reader.line_num,
                    )
    except UnicodeError:
        add_issue("encoding_error", f"Input cannot be decoded as {encoding}.")
    except LookupError:
        add_issue("encoding_error", f"Unknown encoding: {encoding}.")
    except csv.Error as error:
        add_issue("csv_error", str(error), reader.line_num if reader is not None else None)
    except OSError as error:
        add_issue("io_error", error.strerror or str(error))

    if report.columns is None and report.issue_count == 0:
        add_issue("empty_file", "No CSV records found.")
    return report
