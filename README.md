# CSV Sanity

A small command-line tool that checks CSV structure before a file reaches your
spreadsheet, import job, or data pipeline. It reads records incrementally and
has **no runtime dependencies**. Python 3.10 or newer is required.

## What it checks

- Blank or duplicate column headers, after trimming whitespace. Names remain case-sensitive.
- Rows with too many or too few fields.
- CSV parsing errors such as an unterminated quoted field.
- Encoding errors, unreadable files, and empty input.

Quoted commas, escaped quotes, and quoted multiline fields are supported. UTF-8
byte-order marks are handled by default. Inputs are never modified.

## Install from this repository

```sh
python -m pip install .
```

Run the install command from the directory containing `pyproject.toml`.
The project is not currently published to PyPI.

## Use

```sh
csv-sanity examples/valid.csv
csv-sanity examples/invalid.csv --json
csv-sanity first.csv second.csv
csv-sanity data.tsv --delimiter tab
csv-sanity european.csv --delimiter ";" --encoding cp1252
csv-sanity no-headers.csv --no-header
```

The module entry point works too: `python -m csv_sanity examples/valid.csv`.

For `examples/invalid.csv`, the text output is:

```text
FAIL examples/invalid.csv: 2 data rows, 1 issue(s)
  line 3: row_width: Expected 2 fields, found 1.
```

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Every input passed |
| 1 | At least one input has a validation, parsing, decoding, or file access issue |
| 2 | Invalid command-line arguments |

`--json` prints an array with one report per input. A report includes `path`,
`valid`, `data_rows`, `columns`, `issue_count`, and `issues`. Issue objects
contain `code`, `message`, and `line` (null when no reliable line is available).

For example:

```json
[
  {
    "path": "examples/invalid.csv",
    "data_rows": 2,
    "columns": 2,
    "issue_count": 1,
    "issues": [
      {
        "code": "row_width",
        "message": "Expected 2 fields, found 1.",
        "line": 3
      }
    ],
    "valid": false
  }
]
```

Example pipeline check after installing the tool:

```sh
csv-sanity export.csv --json > validation.json
```

The command returns a failing exit code if validation fails, suitable for a CI step.

## Python API

```python
from csv_sanity import validate

report = validate("export.csv", max_issues=10)
if not report.valid:
    for issue in report.issues:
        print(issue.code, issue.line, issue.message)
```

## Behavior and limits

- The first nonempty CSV record is the header unless `--no-header` is set. A header-only file is valid.
- Empty physical records are skipped. A row containing delimiters or quoted empty strings still counts.
- Line numbers refer to the final physical line of a CSV record. A record with quoted newlines can span several lines.
- The delimiter is explicit: comma by default. Delimiter detection is not attempted.
- At most 50 issue details are retained per file by default. Change this with `--max-issues`. Scanning continues so `issue_count` includes all detectable structural issues.
- CSV parsing or decoding failures stop processing the affected file. Row counts describe the records successfully parsed before the failure.
- Memory use grows with the largest record, header size, and retained issues, rather than the total number of rows. Python's CSV field-size limit still applies; an oversized field is reported as a CSV parsing error.
- This is a structural checker. It does not validate data types, business rules, spreadsheet formulas, or duplicate data rows. Passing does not guarantee an import will succeed.
- Reports omit cell contents and header names, but include file paths. Review paths before sharing reports publicly.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
```

The included GitHub Actions workflow runs the tests on Linux and Windows with
Python 3.10, 3.12, and 3.13. Local checks do not require third-party test libraries.

## Project status

This is a new project, version 0.1.0. External usage, downstream dependents, and
download statistics have not yet been established. Bug reports, concrete CSV
edge cases, and documentation improvements are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

MIT. See [LICENSE](LICENSE).
