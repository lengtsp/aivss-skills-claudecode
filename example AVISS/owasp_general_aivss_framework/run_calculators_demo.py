"""Non-interactive demo runner for OWASP's V1/V2/V3 general-AIVSS
calculators, using the same conceptual "moderate-high risk" scenario across
versions so their outputs are directly comparable.

Not a vendored OWASP file -- written for this repo to make the version
comparison reproducible without manually answering interactive prompts.
Uses the same stdin-patching technique OWASP's own test_aivss_calculatorV4.py
already uses for V4 (see that file's run_scenario() helper) -- does not
modify any of the vendored aivss_calculatorV*.py files.

Run from this folder:
    python3 run_calculators_demo.py
"""
import importlib.util
import io
import sys
import warnings
from pathlib import Path

DIR = Path(__file__).resolve().parent


def run_module_stdin(path, inputs_str, call_fn=True):
    old_stdin, old_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(inputs_str)
    sys.stdout = io.StringIO()
    try:
        spec = importlib.util.spec_from_file_location("mod", path)
        mod = importlib.util.module_from_spec(spec)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            spec.loader.exec_module(mod)
            score = mod.calculate_aivss_score() if call_fn else getattr(mod, "aivss_score", None)
            deprecation = [str(x.message) for x in w if issubclass(x.category, DeprecationWarning)]
        out = sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = old_stdin, old_stdout
    return score, out, deprecation


def main():
    print("=" * 72)
    print("V1 (aivss_calculatorV1.py) -- deprecated, free-form 0.0-1.0 inputs")
    print("=" * 72)
    v1_inputs = "1\n1\n1\n1\n1\n0.7\n0.7\n0.7\n0.7\n0.7\n0.7\n0.7\n0.7\n0.7\n"
    score, out, dep = run_module_stdin(str(DIR / "aivss_calculatorV1.py"), v1_inputs, call_fn=False)
    print(out)
    print("Deprecation warning:", dep[0] if dep else "(none raised)")

    print()
    print("=" * 72)
    print("V2 (aivss_calculatorV2.py) -- deprecated, menu-driven, still 5 AI metrics")
    print("=" * 72)
    v2_inputs = "1\n1\n1\n1\n2\n2\n2\n2\n2\n2\n4\n4\n4\n4\n"
    score, out, dep = run_module_stdin(str(DIR / "aivss_calculatorV2.py"), v2_inputs, call_fn=False)
    print(out)
    print("Deprecation warning:", dep[0] if dep else "(none raised)")

    print()
    print("=" * 72)
    print("V3 (aivss_calculatorV3.py) -- full 9-metric spec formula, not deprecated")
    print("=" * 72)
    v3_inputs = (
        "1\n1\n1\n1\n1\n"
        "2\n2\n2\n2\n2\n2\n2\n2\n2\n"
        "2\n"
        "2\n2\n2\n2\n"
        "1\n1\n1\n"
        "2\n2\n2\n2\n"
        "2\n"
    )
    score, out, dep = run_module_stdin(str(DIR / "aivss_calculatorV3.py"), v3_inputs, call_fn=True)
    print(out)

    print()
    print("(V4 is exercised separately -- see test_aivss_calculatorV4.py, the")
    print(" official OWASP demo suite, which covers 10 real-world scenarios.)")


if __name__ == "__main__":
    main()
