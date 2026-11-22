"""Command-line interface for CSV Sanity."""

from __future__ import annotations

import argparse
import json

from . import __version__
from .validator import validate


def positive_integer(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a positive integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def delimiter_value(value: str) -> str:
    delimiter = "\t" if value == "tab" else value
    if len(delimiter) != 1 or delimiter in "\r\n\0\"":
        raise argparse.ArgumentTypeError("use one character, or 'tab' for TSV")
    return delimiter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check CSV structure without changing your files.")
    parser.add_argument("files", nargs="+", help="CSV files to validate")
    parser.add_argument("--delimiter", type=delimiter_value, default=",", help="field separator; use 'tab' for TSV")
    parser.add_argument("--encoding", default="utf-8-sig", help="input encoding (default: utf-8-sig)")
    parser.add_argument("--no-header", action="store_true", help="treat the first record as data")
    parser.add_argument("--max-issues", type=positive_integer, default=50, help="maximum issue details per file (default: 50)")
    parser.add_argument("--json", action="store_true", help="print a JSON array of reports")
    parser.add_argument("--version", action="version", version=f"csv-sanity {__version__}")
    options = parser.parse_args(argv)
    reports = [validate(
        path,
        delimiter=options.delimiter,
        encoding=options.encoding,
        header=not options.no_header,
        max_issues=options.max_issues,
    ) for path in options.files]
    if options.json:
        print(json.dumps([report.to_dict() for report in reports], indent=2, ensure_ascii=True))
    else:
        for report in reports:
            status = "PASS" if report.valid else "FAIL"
            print(f"{status} {report.path}: {report.data_rows} data rows, {report.issue_count} issue(s)")
            for issue in report.issues:
                location = f"line {issue.line}: " if issue.line is not None else ""
                print(f"  {location}{issue.code}: {issue.message}")
            omitted = report.issue_count - len(report.issues)
            if omitted:
                print(f"  {omitted} additional issue(s) omitted.")
    return 0 if all(report.valid for report in reports) else 1
