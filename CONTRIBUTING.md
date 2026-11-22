# Contributing

Thanks for helping improve CSV Sanity. Please open an issue describing the
problem and a minimal sample with invented data. Do not upload private exports.

For code changes:

1. Fork the repository and create a branch for one focused change.
2. Install locally with `python -m pip install -e .`.
3. Add a regression test for a behavior change or bug fix.
4. Run `python -m unittest discover -s tests -v`.
5. Open a pull request describing the problem, the change, and the checks you ran.

Keep the default installation free of runtime dependencies. Preserve the documented
exit codes and JSON fields, or explain proposed compatibility changes in an issue.
Contributions are licensed under the project's MIT license.
