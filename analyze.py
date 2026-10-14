"""
Command-line interface for the Driver's-License Visual Field Analyzer.

Parses a ZEISS Humphrey "driver's-license" visual-field PDF with the native
vector parser, runs the six-rule fitness engine, and prints the verdict.
Optionally writes a patient-facing A4 HTML report.

Examples::

    python analyze.py sample_data/sample_OS.pdf
    python analyze.py path/to/report.pdf --lang en --report-out out/
"""
import argparse
import os
import sys

# --- make the package importable (same layout as app.py) ---
if getattr(sys, "frozen", False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)
_pkg = os.path.join(_BASE, "visual_field_analyzer")
if os.path.isdir(_pkg) and not getattr(sys, "frozen", False):
    sys.path.insert(0, _pkg)

from pdf_parser import parse_pdf          # noqa: E402
from engine import analyze                # noqa: E402
from report_generator import generate_a4_report  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Analyze a ZEISS Humphrey driver's-license visual-field PDF.")
    ap.add_argument("pdf", help="path to the visual-field PDF report")
    ap.add_argument("--lang", choices=["zh", "en"], default="zh",
                    help="language for the printed verdict and report (default: zh)")
    ap.add_argument("--report-out", default=None,
                    help="optional directory to write the A4 HTML report into")
    args = ap.parse_args(argv)

    if not os.path.exists(args.pdf):
        print(f"[error] file not found: {args.pdf}", file=sys.stderr)
        return 2

    rep = parse_pdf(args.pdf)
    if rep is None or rep.eye not in ("OS", "OD"):
        print("[error] could not parse a valid OS/OD report from this PDF.",
              file=sys.stderr)
        return 1

    # Unknown (-1) points are treated as "seen" for the fitness decision,
    # matching the GUI workflow where the clinician confirms ambiguous points.
    states = [1 if s == 1 else 0 for s in (rep.point_states or [1] * 99)]
    res = analyze(rep.eye, states, rep.fixation_loss,
                  rep.false_positive, rep.false_negative, lang=args.lang)

    eye_name = "Left (OS)" if res.eye == "OS" else "Right (OD)"
    print(f"Eye tested : {eye_name}")
    print(f"Fixation loss / False positive / False negative : "
          f"{rep.fixation_loss} / {rep.false_positive} / {rep.false_negative}")
    print("-" * 52)
    for r in res.rules:
        mark = "PASS" if r.passed else "FAIL"
        print(f"  Rule {r.rule_id} [{mark}] {r.rule_name}")
        print(f"           {r.detail}")
    print("-" * 52)
    print(res.summary)

    if args.report_out:
        out = generate_a4_report(rep, res, args.report_out, lang=args.lang)
        print(f"\nA4 report written to: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
