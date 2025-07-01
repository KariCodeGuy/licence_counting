LLM Agent – Development Instructions
1. Style Guide
Follow PEP 8 for all Python code.

Use Black to auto-format code. Formatting is enforced on every commit.

Use type hints throughout (PEP 484).

Use NumPy-style docstrings for all functions and classes (PEP 257).

2. Tooling
Use Python 3.11

Recommended IDEs: VSCode, Cursor, or PyCharm

Enable the following IDE settings:

Auto Docstring: Format = numpy

Lint on Save: ✅

Formatter: black

Linting Enabled: ✅

3. Environment
Use uv as the default package manager.

bash
Copy
Edit
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
Alternatively, use miniconda if GPU or RAPIDS libraries are needed.

4. Git Discipline
Every code change must be committed to Git.

Use clear commit messages and commit after each meaningful update (e.g., new method, bug fix, test added).

bash
Copy
Edit
git add .
git commit -m "Add X module with docstrings and type hints"
git push
5. Documentation
Every file must have a module-level docstring.

Every function and class must include a NumPy-style docstring.

Use the autoDocstring extension to generate boilerplate docstrings.

6. Testing
Use pytest or unittest to write unit tests and integration tests.

Keep tests fast, self-contained, and meaningful.

Add regression tests when bugs are fixed.

Include a tests/ directory and ensure coverage for all core logic.