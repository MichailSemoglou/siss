# Contributing to Siss

Thank you for considering a contribution. This document describes how to set up
the project, run checks, and submit changes.

## Setup

1. Fork the repository and clone your fork:

   ```bash
   git clone https://github.com/<your-username>/siss.git
   cd siss
   ```

2. Create a virtual environment and install the package in editable mode:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. Install the development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

## Workflow

1. Create a feature branch from `main`:

   ```bash
   git checkout -b feature/short-description
   ```

2. Make your changes. Run the lint and test suite before committing:

   ```bash
   ruff check src/ tests/
   mypy
   pytest
   ```

3. Commit your changes. Follow the commit-message convention described below.

4. Push to your fork and open a pull request against `main`.

5. In the pull request body, describe what changed, why, and what a reviewer
   should check.

## Commit-Message Convention

- Subject line in the imperative present tense, no trailing period, 72
  characters or fewer.
- An optional area prefix is acceptable: `area: brief description`.
- Separate copy edits from code changes so each commit is reviewable on its
  own.

```text
# Good
halftone: add slash symbol rendering
fix import ordering in duotone module
Add still-image input support

# Bad
added halftone slash symbol rendering.
fixed stuff
```

## Running Checks

| Command                  | Purpose                        |
| ------------------------ | ------------------------------ |
| `ruff check src/ tests/` | Lint and import ordering       |
| `mypy`                   | Static type checking           |
| `pytest`                 | Run the test suite             |
| `pytest --cov=siss`      | Run tests with coverage report |

## Project Conventions

American spelling throughout. Markdown prose uses curly quotation marks.
Docstrings, code comments, and error messages use straight ASCII characters. No contractions. Docstrings follow numpydoc style.

## Reporting Issues

Use the [bug report](https://github.com/MichailSemoglou/siss/issues/new?template=bug_report.md)
or [feature request](https://github.com/MichailSemoglou/siss/issues/new?template=feature_request.md)
templates to open an issue.

## Security

Report vulnerabilities privately via GitHub's **Report a vulnerability**
button on the [Security](https://github.com/MichailSemoglou/siss/security)
tab. Do not open a public issue. See `SECURITY.md` for the full policy.
