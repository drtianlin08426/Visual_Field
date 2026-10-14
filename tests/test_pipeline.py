"""
End-to-end and unit tests for the driver's-license visual-field analyzer.

These tests need NO real patient data: they build synthetic ZEISS-like
report PDFs with :mod:`make_sample_pdf`, parse them with the native-vector
parser, and check the six-rule engine.

Run with::

    python tests/test_pipeline.py          # standalone
    pytest tests/test_pipeline.py          # or with pytest
"""
import os
import sys
import tempfile

import fitz  # PyMuPDF (only used indirectly; kept for import-time clarity)

# Make the package importable whether run from repo root or tests/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "visual_field_analyzer"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from point_grid import (  # noqa: E402
    get_points_for_eye, get_temporal_outer_point, get_nasal_edge_indices,
    get_horizontal_band_indices,
)
from pdf_parser import parse_pdf  # noqa: E402
from engine import analyze  # noqa: E402
from make_sample_pdf import make_sample  # noqa: E402


def _tmp_pdf(eye="OS", unseen_indices=None, fl=0, fp=0, fn=0):
    d = tempfile.mkdtemp(prefix="vf_test_")
    path = os.path.join(d, f"sample_{eye}.pdf")
    make_sample(path, eye=eye, unseen_indices=unseen_indices,
                fixation_loss=fl, false_positive=fp, false_negative=fn)
    return path


def test_parse_and_detect_accuracy():
    """A synthetic 'fail' report is parsed and detected with 0 mismatches."""
    eye = "OS"
    t = get_temporal_outer_point(eye)
    n = get_nasal_edge_indices(eye)
    band = get_horizontal_band_indices(eye)
    unseen = set([t] + list(n) + [band[0], band[1], band[2]])

    path = _tmp_pdf(eye=eye, unseen_indices=unseen)
    rep = parse_pdf(path)
    assert rep is not None, "parse_pdf returned None"
    assert rep.eye == eye, f"eye mismatch: {rep.eye}"
    assert rep.point_states is not None, "point_states is None"
    assert len(rep.point_states) == 99

    mismatch = sum(1 for i in range(99)
                   if (i in unseen) != (rep.point_states[i] == 0))
    assert mismatch == 0, f"{mismatch} point-state mismatches vs intended"


def test_engine_fail_case():
    """Temporal-outer miss + 3 consecutive band misses + 0 nasal => FAIL."""
    eye = "OS"
    t = get_temporal_outer_point(eye)
    n = get_nasal_edge_indices(eye)
    band = get_horizontal_band_indices(eye)
    unseen = set([t] + list(n) + [band[0], band[1], band[2]])

    path = _tmp_pdf(eye=eye, unseen_indices=unseen)
    rep = parse_pdf(path)
    states = [1 if s == 1 else 0 for s in (rep.point_states or [1] * 99)]
    res = analyze(eye, states, rep.fixation_loss, rep.false_positive,
                  rep.false_negative)
    assert res.overall_pass is False
    failed_ids = {r.rule_id for r in res.rules if not r.passed}
    assert {3, 4, 5}.issubset(failed_ids), f"expected 3/4/5 to fail, got {failed_ids}"


def test_engine_pass_case():
    """All points seen => PASS."""
    eye = "OS"
    path = _tmp_pdf(eye=eye, unseen_indices=[])
    rep = parse_pdf(path)
    states = [1 if s == 1 else 0 for s in (rep.point_states or [1] * 99)]
    res = analyze(eye, states, 0, 0, 0)
    assert res.overall_pass is True


def test_rule6_conditional():
    """With >=2 fixation losses and 0 nasal-edge correct => rule 6 FAIL."""
    eye = "OS"
    n = get_nasal_edge_indices(eye)
    path = _tmp_pdf(eye=eye, unseen_indices=list(n), fl=2, fp=0, fn=0)
    rep = parse_pdf(path)
    states = [1 if s == 1 else 0 for s in (rep.point_states or [1] * 99)]
    res = analyze(eye, states, rep.fixation_loss, rep.false_positive,
                  rep.false_negative)
    r6 = next(r for r in res.rules if r.rule_id == 6)
    assert r6.passed is False, "rule 6 should fail when triggered with 0 nasal"


def test_engine_boundaries():
    """Direct unit checks of each rule's pass/fail boundary."""
    eye = "OS"
    all_seen = [1] * 99

    # Rule 1: fixation loss <= 3
    assert analyze(eye, list(all_seen), 3, 0).overall_pass is True
    assert analyze(eye, list(all_seen), 4, 0).overall_pass is False

    # Rule 2: false positive <= 3
    assert analyze(eye, list(all_seen), 0, 3).overall_pass is True
    assert analyze(eye, list(all_seen), 0, 4).overall_pass is False

    # NOTE: the 4 nasal-edge points sit inside the horizontal +-10 deg band, so
    # zeroing them can also trip rule 4. We therefore assert each rule's own
    # ``passed`` flag rather than the aggregate ``overall_pass``.
    def _rule(res, rid):
        return next(r for r in res.rules if r.rule_id == rid)

    # Rule 3: temporal outer point must be seen
    s3 = list(all_seen); s3[get_temporal_outer_point(eye)] = 0
    assert _rule(analyze(eye, s3, 0, 0), 3).passed is False

    # Rule 4: < 3 consecutive unseen within horizontal band
    band = get_horizontal_band_indices(eye)
    s4 = list(all_seen)
    s4[band[0]] = s4[band[1]] = 0
    assert _rule(analyze(eye, s4, 0, 0), 4).passed is True
    s4[band[2]] = 0
    assert _rule(analyze(eye, s4, 0, 0), 4).passed is False

    # Rule 5: >= 1 of 4 nasal-edge points seen
    nose = get_nasal_edge_indices(eye)
    s5 = list(all_seen)
    for i in nose:
        s5[i] = 0
    assert _rule(analyze(eye, s5, 0, 0), 5).passed is False
    s5[nose[0]] = 1
    assert _rule(analyze(eye, s5, 0, 0), 5).passed is True

    # Rule 6: only triggers when fl>=2 or fp>=2; needs >=2 nasal correct then
    # not triggered (fl<2, fp<2) -> auto pass even if nasal edge all unseen
    s6 = list(all_seen)
    for i in nose:
        s6[i] = 0
    assert _rule(analyze(eye, s6, 1, 1), 6).passed is True
    # triggered, 0 nasal correct -> rule 6 fails
    assert _rule(analyze(eye, s6, 2, 0), 6).passed is False
    # triggered, >=2 nasal correct -> rule 6 passes
    s6c = list(all_seen)
    s6c[nose[2]] = 0
    s6c[nose[3]] = 0  # 2 of 4 correct
    assert _rule(analyze(eye, s6c, 2, 0), 6).passed is True


def _run_all():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    ok = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
            ok += 1
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"ERROR {fn.__name__}: {e}")
    print(f"\n{ok}/{len(fns)} tests passed")
    return ok == len(fns)


if __name__ == "__main__":
    import sys as _sys
    success = _run_all()
    _sys.exit(0 if success else 1)
