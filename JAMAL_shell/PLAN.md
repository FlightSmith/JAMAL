# Python Script Plan: Argument Parsing and Logging

**Goal:** Create a robust Python script (`main.py`) for processing a file specified via command line, featuring configurable logging (`utils/logger.py`) and argument parsing (`argparse`), along with a placeholder for the core processing logic (`jamal/core/parser.py`).

**Plan:**

1.  **Establish Project Structure:**
    *   Create the directory `utils/`.
    *   Create the directory `jamal/`.
    *   Create the subdirectory `jamal/core/`.

2.  **Implement Logging Utility (`utils/logger.py`):**
    *   Create the file `utils/logger.py`.
    *   Import the `logging` module.
    *   Define a function `setup_logging(log_level: int = logging.WARNING) -> None`:
        *   Include a docstring explaining its purpose.
        *   Configure `logging.basicConfig` with:
            *   `level=log_level`
            *   `format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"`
            *   `datefmt="%Y-%m-%d %H:%M:%S"`

3.  **Create Placeholder Parser (`jamal/core/parser.py`):**
    *   Create the file `jamal/core/parser.py`.
    *   Import `os` and `logging`.
    *   Define a class `MatrixParser`:
        *   Include a basic docstring.
        *   Define `__init__(self, filepath: str) -> None`:
            *   Include a docstring.
            *   Store `filepath`.
            *   Log an info message (e.g., `MatrixParser initialized for file: {filepath}`).
            *   *(Optional but good practice)* Check if the file exists using `os.path.exists` and raise `FileNotFoundError` if not.
        *   Define a placeholder method `process(self) -> None`:
            *   Include a docstring.
            *   Log an info message (e.g., `Processing file: {self.filepath}`).
            *   *(Placeholder logic - can just pass or log)*

4.  **Implement Main Script (`main.py`):**
    *   Create the file `main.py`.
    *   Define `__version__ = '0.1.0'`.
    *   Import necessary modules: `argparse`, `logging`, `sys`, `os`.
    *   Import `setup_logging` from `utils.logger`.
    *   Import `MatrixParser` from `jamal.core.parser`.
    *   Define a `main()` function:
        *   Include a docstring.
        *   Create an `argparse.ArgumentParser` instance with a description.
        *   Add the `filepath` positional argument with `help`.
        *   Add the `-v`, `--version` argument using `action='version'`.
        *   Add the `-q`, `--quiet` argument using `action='store_true'`, `help`.
        *   Add the `-d`, `--debug` argument using `action='count'`, `default=0`, `help`.
        *   Parse arguments using `parser.parse_args()`.
        *   **Argument Validation:** Check if `args.quiet` and `args.debug > 0`. If true, use `parser.error("Arguments -q/--quiet and -d/--debug are mutually exclusive")` to print an error and exit.
        *   **Determine Log Level:**
            *   If `args.quiet`: `log_level = logging.ERROR`
            *   Else if `args.debug == 1`: `log_level = logging.INFO`
            *   Else if `args.debug >= 2`: `log_level = logging.DEBUG`
            *   Else: `log_level = logging.WARNING` (default)
        *   Call `setup_logging(log_level)`.
        *   Log script start and the effective log level: `logging.info("Script started. Log level set to %s", logging.getLevelName(log_level))`.
        *   Log the file being processed: `logging.info("Processing file: %s", args.filepath)`.
        *   **Core Logic Execution (with Error Handling):**
            *   Start a `try` block.
            *   Instantiate `parser_instance = MatrixParser(args.filepath)`.
            *   Call `parser_instance.process()`.
            *   Log success: `logging.info("Processing completed successfully.")`.
            *   `except FileNotFoundError as e:`
                *   Log the error: `logging.error("Input file not found: %s", e)`.
                *   `sys.exit(1)`.
            *   `except Exception:`
                *   Log the exception with traceback: `logging.exception("An unexpected error occurred during processing.")`.
                *   `sys.exit(1)`.
    *   Use the standard `if __name__ == "__main__":` guard to call `main()`.

**Mermaid Diagram (File Structure & High-Level Flow):**

```mermaid
graph TD
    subgraph "Project Files"
        A(main.py)
        B(utils/logger.py)
        C(jamal/core/parser.py)
    end

    subgraph "Execution Flow (main.py)"
        Start --> ParseArgs[Parse Command Line Arguments];
        ParseArgs --> ValidateArgs{Validate -q/-d Exclusivity};
        ValidateArgs -- Valid --> SetLogLevel[Determine & Set Log Level];
        ValidateArgs -- Invalid --> ErrorExit[Error & Exit];
        SetLogLevel --> LogStart[Log Script Start];
        LogStart --> TryProcess{Try Processing};
        TryProcess -- Instantiate --> C;
        C -- process() --> TryProcess;
        TryProcess -- Success --> LogSuccess[Log Success];
        TryProcess -- FileNotFoundError --> LogFileNotFound[Log File Not Found Error];
        TryProcess -- Other Exception --> LogGenericError[Log Generic Error];
        LogFileNotFound --> ExitError[Exit(1)];
        LogGenericError --> ExitError;
        LogSuccess --> End[End Script];
    end

    A -- imports & calls --> B(setup_logging);
    A -- imports & instantiates --> C(MatrixParser);
```

---

# Testing Plan for `_validate_field` in `app/core/parser.py`

This plan focuses on creating unit tests for the `_validate_field` method within the `MatrixParser` class, located in [`app/core/parser.py`](app/core/parser.py).

**1. Analysis of `_validate_field` and its Dependencies:**

*   **Target Function:** [`_validate_field(self, column_name: str, value: str) -> bool`](app/core/parser.py:74-126)
*   **Key Inputs:**
    *   `column_name`: String, used to look up configuration in `self.column_config`.
    *   `value`: String, the actual data to be validated.
*   **Core Dependencies:**
    *   `self.column_config` (derived from [`COLUMN_CONFIG`](app/core/parser.py:14-41) in the module): This dictionary dictates the validation rules (`validator`, `allowed_values`, `expected_length`, `bracketed`).
    *   [`app.utils.transformers.extract_bracketed_value`](app/utils/transformers.py:12-42): Pre-processes the `value` based on `bracketed` configuration.
    *   Validator functions within [`app.utils.validators`](app/utils/validators.py) (e.g., [`validate_integer`](app/utils/validators.py:11-17), [`validate_choice`](app/utils/validators.py:93-95), etc.): Dynamically called based on the `validator` string in the config.
*   **Key Behaviors to Test:**
    *   Correct lookup and application of validation rules from `COLUMN_CONFIG`.
    *   Proper handling of single vs. list of validators.
    *   Interaction with `extract_bracketed_value` for `bracketed` fields (both valid and invalid bracket usage).
    *   Correct delegation to validator functions in `app.utils.validators`.
    *   Handling of missing validator configurations (should default to `True`).
    *   Handling of missing validator methods (logs a warning, continues if multiple validators, effectively means that specific check is skipped).
    *   Correct passing of special arguments (`allowed_values`, `expected_length`) to relevant validators.
    *   Return `True` for valid fields, `False` for invalid fields.

**2. Testing Strategy:**

*   **Type of Tests:** **Unit Tests**.
    *   **Justification:** Unit tests are ideal for testing the `_validate_field` method in isolation. We can mock its dependencies (`self.column_config`, and indirectly, the actual validator functions if we want to test the dispatch logic separately from the validators' correctness) or, more practically for this scenario, provide various `COLUMN_CONFIG` snippets and test against the real validator functions since they are also part of the unit's behavior. This allows for precise control over inputs and verification of outputs and interactions.
*   **Recommended Tools & Frameworks:**
    *   **`pytest`**: A popular, powerful, and Pythonic testing framework. It offers a simple syntax, powerful fixture support, and good integration with other tools.
    *   **`unittest.mock.patch` (if needed)**: For mocking parts of `self.column_config` or specific validator functions if extremely granular isolation is desired, though for `_validate_field`, testing with concrete mini-configs is often more straightforward and covers more ground.
*   **Test Structure:**
    *   Tests will typically involve creating an instance of `MatrixParser`.
    *   Setting up or patching `parser_instance.column_config` for specific test cases.
    *   Calling `parser_instance._validate_field(column_name, value)` with various inputs.
    *   Asserting the boolean return value.
    *   Optionally, asserting that specific log messages were generated (e.g., for missing validators or configuration issues).

**3. Crucial Test Scenarios for `_validate_field`:**

We'll need to cover various combinations of configurations and input values.

*   **Scenario 1: Basic Validation (No Brackets)**
    *   Test with `validator: "integer"`:
        *   Valid integer string (e.g., "123") -> `True`
        *   Invalid integer string (e.g., "abc", "1.2") -> `False`
    *   Test with `validator: "string"`:
        *   Non-empty string (e.g., "hello") -> `True`
        *   Empty string (e.g., "") -> `False` (based on `bool(value)`)
    *   Test with `validator: "choice"`, `allowed_values: ["A", "B"]`:
        *   Valid choice (e.g., "A") -> `True`
        *   Invalid choice (e.g., "C") -> `False`
        *   Config missing `allowed_values` -> `False` (and log warning)
    *   Test with `validator: "comma_separated_numbers"`, `expected_length: 2`:
        *   Valid (e.g., "1.0,2.5") -> `True`
        *   Valid with '-' (e.g., "-,2.5") -> `True`
        *   Invalid (e.g., "1.0,abc") -> `False`
        *   Wrong length (e.g., "1.0") -> `False`
        *   Config missing `expected_length` -> `False` (and log warning)
    *   Test with `validator: "numeric_range"`:
        *   Valid single float ("0.5") -> `True`
        *   Valid range ("0.1:0.1:0.5") -> `True`
        *   Valid multi-range ("0.1:0.1:0.5,1.0:0.2:2.0") -> `True`
        *   Invalid range ("0.1:0.5") -> `False`
        *   Empty string -> `False`

*   **Scenario 2: Bracketed Field Validation (`bracketed: True`)**
    *   Column `TEST_BRACKET` with `validator: "integer"`, `bracketed: True`
        *   `value = "[123]"` -> `True` (validates "123")
        *   `value = "[abc]"` -> `False` (validates "abc" against integer)
        *   `value = "123"` (no brackets, but config expects them) -> `True` (validates "123" as per `extract_bracketed_value` logic)
        *   `value = "[123"` (mismatched brackets) -> `False` (due to `extract_bracketed_value` returning `None`)
        *   `value = "1[2]3"` (misplaced brackets) -> `False`

*   **Scenario 3: Bracketed Field Misconfiguration (`bracketed: False` but value has brackets)**
    *   Column `TEST_NO_BRACKET` with `validator: "integer"`, `bracketed: False`
        *   `value = "[123]"` -> `False` (due to `extract_bracketed_value` returning `None`)

*   **Scenario 4: Configuration Edge Cases**
    *   No `validator` specified for a column -> `True`
    *   `validator` is an unknown string (e.g., `"non_existent_validator"`) -> `True` (logs warning, effectively skips this validator). If it's the only validator, the field passes.
    *   `validator` is a list: `["integer", "choice"]` (assuming choice is compatible, e.g. allowed_values are "1", "2")
        *   Value passes both -> `True`
        *   Value fails first -> `False`
        *   Value passes first, fails second -> `False`

*   **Scenario 5: Multiple Validators**
    *   `COLUMN_CONFIG = {"MULTI_TEST": {"validator": ["string", "choice"], "allowed_values": ["ABC", "DEF"]}}`
        *   `_validate_field("MULTI_TEST", "ABC")` -> `True`
        *   `_validate_field("MULTI_TEST", "GHI")` -> `False` (fails choice)
        *   `_validate_field("MULTI_TEST", "")` -> `False` (fails string)

**4. Implementation Sequence (for `_validate_field` tests):**

1.  Create a test file (e.g., `tests/core/test_parser.py`).
2.  Import `MatrixParser` and `pytest`.
3.  Write test functions, each covering one or more scenarios from above.
    *   Use `pytest.mark.parametrize` extensively to test various inputs and configurations efficiently.
    *   Instantiate `MatrixParser` (filepath can be a dummy non-existent one if `process()` isn't called, or a temp file).
    *   For each test case or parameterized input:
        *   Set `parser_instance.column_config` to the specific configuration needed for that test.
        *   Call `parser_instance._validate_field(col, val)`.
        *   Assert the result.
        *   (Optional) Use `caplog` fixture from `pytest` to assert log messages for warning/error conditions.

**5. Markdown for `README.MD` (focused on `_validate_field` tests):**

This will be a preliminary section, as the full project testing strategy is broader.

```markdown
## Executing the Tests

This project uses `pytest` for testing.

### Prerequisites

Ensure you have `pytest` installed in your Python environment:

```bash
pip install pytest
```

### Running Tests for `_validate_field`

To run the unit tests specifically for the `_validate_field` method in `app.core.parser.MatrixParser`, you can target the specific test file or use markers if implemented.

Assuming the tests for `MatrixParser` are located in `tests/core/test_parser.py`:

```bash
pytest tests/core/test_parser.py
```

If specific markers are used (e.g., `@pytest.mark.validate_field`), you could run:

```bash
pytest -m validate_field
```

(Further instructions for running the complete test suite will be added as more tests are developed.)