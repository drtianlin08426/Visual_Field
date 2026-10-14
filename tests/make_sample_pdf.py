"""
Generate a DE-IDENTIFIED, fully synthetic ZEISS Humphrey "driver's-license"
visual-field report PDF.

The generated file mimics the *vector drawing primitives* used by real ZEISS
reports so that the native-vector parser
(:func:`visual_field_analyzer.pdf_parser.detect_point_states_from_vector`)
can be exercised end-to-end WITHOUT any real patient data:

  * 9 gray concentric circles (fixation point + 9 rings of 10 deg each) define
    the fixation centre ``(fx, fy)`` and the pixels-per-degree scale ``ppd``.
  * "Seen" points are white-filled, black-stroked circles (4 cubic-bezier arcs),
    exactly as ZEISS emits them.
  * "Unseen" points are small black-filled squares (rectangles).

A canonical grid point ``(gx_deg, gy_deg)`` is placed at::

    px = fx + gx_deg / 10 * ppd
    py = fy - gy_deg / 10 * ppd

This mirrors the inverse transform in the parser, so the greedy nearest-symbol
matching recovers the intended state vector with ~100% accuracy.

Usage::

    python make_sample_pdf.py                # writes ../sample_data/sample_OS.pdf
    python make_sample_pdf.py --eye OD --out my.pdf
"""
import os
import sys
import argparse

import fitz  # PyMuPDF

try:
    from visual_field_analyzer.point_grid import get_points_for_eye
except ImportError:  # allow running from inside tests/ as a script
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "visual_field_analyzer"))
    from point_grid import get_points_for_eye

# Colours (RGB, 0-1 floats) matching ZEISS vector primitives
GRAY = (0.8, 0.8, 0.8)
SEEN_STROKE = (0.0, 0.0, 0.0)
SEEN_FILL = (1.0, 1.0, 1.0)
UNSEEN_FILL = (0.0, 0.0, 0.0)

PAGE_W, PAGE_H = 600.0, 760.0


def make_sample(out_path, eye="OS", unseen_indices=None,
                fixation_loss=0, false_positive=0, false_negative=0,
                ppd=18.0, center=(300.0, 400.0)):
    """Create one synthetic report PDF.

    Args:
        out_path: destination ``.pdf`` path.
        eye: ``"OS"`` (left) or ``"OD"`` (right).
        unseen_indices: iterable of grid indices (in the order returned by
            ``get_points_for_eye(eye)``) that should be drawn as "unseen".
        fixation_loss / false_positive / false_negative: reliability counters
            written as ``中央 / x/y z/w ...`` text so ``parse_pdf`` reads them.
        ppd: points-per-10-degrees scale of the plotted field (default 18).
        center: (x, y) fixation centre in PDF points.
    """
    unseen = set(unseen_indices or [])
    fx, fy = center
    pts = get_points_for_eye(eye)

    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)

    # 1) 9 gray concentric circles (fixation point + 9 rings of 10 deg)
    for k in range(1, 10):
        sh = page.new_shape()
        sh.draw_circle((fx, fy), k * ppd)
        sh.finish(color=GRAY, fill=None)
        sh.commit()

    # 2) one symbol per canonical grid point
    sym_r = 2.6
    half = 2.7
    for i, (gx, gy) in enumerate(pts):
        px = fx + gx / 10.0 * ppd
        py = fy - gy / 10.0 * ppd
        sh = page.new_shape()
        if i in unseen:
            sh.draw_rect(fitz.Rect(px - half, py - half, px + half, py + half))
            sh.finish(color=UNSEEN_FILL, fill=UNSEEN_FILL)
        else:
            sh.draw_circle((px, py), sym_r)
            sh.finish(color=SEEN_STROKE, fill=SEEN_FILL)
        sh.commit()

    # 3) text labels so parse_pdf can read eye + reliability + seen/unseen counts.
    #    CJK labels use PyMuPDF's built-in Simplified-Chinese font ("china-s");
    #    the default font cannot render Chinese glyphs.
    page.insert_text((40, 40), eye, fontsize=12)
    page.insert_text((40, 70), "中央", fontsize=11, fontname="china-s")
    page.insert_text((40, 90),
                     f"{fixation_loss}/0  {false_positive}/0  {false_negative}/0",
                     fontsize=11)
    n_unseen = len(unseen)
    page.insert_text((40, 120), f"已见 {len(pts) - n_unseen}", fontsize=11,
                     fontname="china-s")
    page.insert_text((40, 140), f"未见 {n_unseen}", fontsize=11,
                     fontname="china-s")
    page.insert_text((40, 600),
                     "DEIDENTIFIED SAMPLE - synthetic test data, not a real patient",
                     fontsize=10)
    page.insert_text((40, 620),
                     "ZEISS Humphrey Field Analyzer - Driver's License Program",
                     fontsize=10)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    doc.save(out_path)
    doc.close()
    return out_path


def _main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eye", choices=["OS", "OD"], default="OS")
    ap.add_argument("--out", default=None,
                    help="output PDF path (default: ../sample_data/sample_<EYE>.pdf)")
    ap.add_argument("--unseen", type=int, nargs="*", default=[],
                    help="grid indices to mark as unseen")
    ap.add_argument("--fl", type=int, default=0, dest="fixation_loss")
    ap.add_argument("--fp", type=int, default=0, dest="false_positive")
    ap.add_argument("--fn", type=int, default=0, dest="false_negative")
    args = ap.parse_args()

    out = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "sample_data", f"sample_{args.eye}.pdf")
    path = make_sample(out, eye=args.eye, unseen_indices=args.unseen,
                       fixation_loss=args.fixation_loss,
                       false_positive=args.false_positive,
                       false_negative=args.false_negative)
    print("Wrote", path)


if __name__ == "__main__":
    _main()
