import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from csv_sanity import validate
from csv_sanity.cli import main


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "input.csv"

    def write(self, content):
        self.path.write_text(content, encoding="utf-8", newline="")
        return self.path

    def test_valid_csv_and_header_only_file(self):
        for content, count in [("name,city\nSara,Cairo\n", 1), ("name,city\n", 0)]:
            with self.subTest(content=content):
                report = validate(self.write(content))
                self.assertTrue(report.valid)
                self.assertEqual(report.data_rows, count)
                self.assertEqual(report.columns, 2)

    def test_width_errors_with_physical_line_numbers(self):
        report = validate(self.write('a,b\n"two\nlines",ok\nmissing\n1,2,3\n'))
        self.assertEqual(report.data_rows, 3)
        self.assertEqual([issue.line for issue in report.issues], [4, 5])
        self.assertEqual([issue.code for issue in report.issues], ["row_width", "row_width"])

    def test_quotes_commas_and_escaped_quotes(self):
        report = validate(self.write('a,b\n"hello, world","say ""hi"""\n'))
        self.assertTrue(report.valid)
        self.assertEqual(report.data_rows, 1)

    def test_header_names_are_trimmed_and_case_sensitive(self):
        report = validate(self.write(" name ,name,Name, ,\n"))
        self.assertEqual([issue.code for issue in report.issues], ["duplicate_header", "blank_header", "blank_header"])
        self.assertEqual(report.columns, 5)

    def test_no_header_uses_first_data_record_width(self):
        report = validate(self.write("1,2\n3,4\n5\n"), header=False)
        self.assertEqual(report.data_rows, 3)
        self.assertEqual(report.issue_count, 1)
        self.assertEqual(report.issues[0].line, 3)

    def test_bom_is_removed(self):
        report = validate(self.write("\ufeffa,a\n1,2\n"))
        self.assertEqual(report.issues[0].code, "duplicate_header")

    def test_blank_physical_records_are_skipped(self):
        report = validate(self.write("\n\na,b\n\n1,2\n\n"))
        self.assertTrue(report.valid)
        self.assertEqual(report.data_rows, 1)

    def test_empty_files_fail(self):
        for content in ["", "\n\r\n"]:
            with self.subTest(content=content):
                report = validate(self.write(content))
                self.assertEqual(report.issues[0].code, "empty_file")

    def test_issue_details_capped_but_all_width_errors_counted(self):
        report = validate(self.write("a,b\n" + "one\n" * 5000), max_issues=2)
        self.assertEqual(report.data_rows, 5000)
        self.assertEqual(report.issue_count, 5000)
        self.assertEqual(len(report.issues), 2)

    def test_invalid_encoding_is_a_report_not_a_traceback(self):
        self.path.write_bytes(b"a,b\n\xff,2\n")
        report = validate(self.path)
        self.assertFalse(report.valid)
        self.assertEqual(report.issues[0].code, "encoding_error")

    def test_custom_encoding(self):
        self.path.write_bytes("name,city\nAndr\u00e9,Paris\n".encode("latin-1"))
        self.assertTrue(validate(self.path, encoding="latin-1").valid)

    def test_unknown_encoding(self):
        report = validate(self.write("a,b\n"), encoding="not-an-encoding")
        self.assertEqual(report.issues[0].code, "encoding_error")

    def test_unclosed_quoted_record(self):
        report = validate(self.write('a,b\n"not closed,2\n'))
        self.assertEqual(report.issues[0].code, "csv_error")
        self.assertEqual(report.issues[0].line, 2)

    def test_missing_file_and_directory(self):
        for path in [self.path, Path(self.directory.name)]:
            with self.subTest(path=path):
                report = validate(path)
                self.assertEqual(report.issues[0].code, "io_error")

    def test_delimiters(self):
        for delimiter in ["\t", ";", "|"]:
            with self.subTest(delimiter=delimiter):
                report = validate(self.write(f"a{delimiter}b\n1{delimiter}2\n"), delimiter=delimiter)
                self.assertTrue(report.valid)
                self.assertEqual(report.columns, 2)

    def test_invalid_options(self):
        for delimiter in ["", "ab", "\n", "\r", "\0", '"']:
            with self.subTest(delimiter=delimiter):
                with self.assertRaises(ValueError):
                    validate(self.path, delimiter=delimiter)
        with self.assertRaises(ValueError):
            validate(self.path, max_issues=0)

    def test_cli_json_includes_successful_and_failing_files(self):
        good = self.write("a,b\n1,2\n")
        bad = Path(self.directory.name) / "bad.csv"
        bad.write_text("a,b\n1\n", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main([str(good), str(bad), "--json"])
        self.assertEqual(result, 1)
        reports = json.loads(output.getvalue())
        self.assertEqual([report["valid"] for report in reports], [True, False])
        self.assertEqual(reports[1]["issues"][0]["line"], 2)

    def test_cli_success_with_tab_and_no_header(self):
        path = self.write("1\t2\n3\t4\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(path), "--delimiter", "tab", "--no-header"]), 0)

    def test_cli_bad_arguments_exit_two(self):
        for arguments in [["--max-issues", "0"], ["--delimiter", "two"], ["--max-issues", "abc"]]:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main([str(self.path), *arguments])
                self.assertEqual(error.exception.code, 2)

    def test_cli_text_shows_truncation(self):
        path = self.write("a,b\n1\n2\n3\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main([str(path), "--max-issues", "1"])
        self.assertEqual(result, 1)
        self.assertIn("line 2: row_width", output.getvalue())
        self.assertIn("2 additional issue(s) omitted.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
