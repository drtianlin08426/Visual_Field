# Driver's-License Visual Field Analyzer

> **Automated fitness-to-drive assessment from ZEISS Humphrey driver's-license
> visual-field (VF) PDF reports, by native vector parsing of the report graphics.**

This repository accompanies the manuscript:

> Lin T, Chen H, et al. *Automated Fitness-to-Drive Assessment via Native Vector
> Parsing of Humphrey Driver-License Visual Field PDFs.*
> **Translational Vision Science & Technology (TVST)** — under review.
> *(Add the DOI / final citation here once the article is accepted.)*

The tool reads a ZEISS Humphrey "驾驶员视野检测" (driver's-license) perimeter PDF,
reconstructs the 99-point monocular test grid directly from the **vector drawing
primitives** in the PDF (no pixel-level OCR), applies the six statutory fitness
criteria, and produces a patient-facing A4 report. A clinician keeps final
authority over the result.

---

## What it does

- **Native vector parsing.** Instead of rasterising the field plot and recognising
  symbols by image processing, the parser walks the PDF's drawing commands
  (`page.get_drawings()`). Gray concentric circles locate the fixation point and
  define the pixels-per-degree scale; white-filled circles and black-filled
  squares are read back as *seen* / *unseen* test points. This avoids the
  overlap/registration and resolution problems of pixel-based approaches.
- **Six rule engine.** A transparent, configurable decision engine encodes the
  monocular fitness criteria used for motor-vehicle driving-license applications.
- **Offline & reproducible.** Pure-Python, no network, no cloud. A synthetic
  sample PDF is included so reviewers can reproduce the full pipeline without
  patient data.
- **Bilingual.** GUI, report, and CLI support 中文 / English.

## The six fitness criteria

Implemented in [`visual_field_analyzer/engine.py`](visual_field_analyzer/engine.py)
and based on the monocular visual-field requirements of the
*Regulation on the Application and Use of Motor Vehicle Driving Licenses*
(中华人民共和国《机动车驾驶证申领和使用规定》). They are expressed here as a
configurable rule set, so the same engine can be retargeted to other standards
(e.g. binocular Esterman) by editing the grid / rule parameters.

| # | Criterion | Limit |
|---|-----------|-------|
| 1 | Fixation loss | ≤ 3 |
| 2 | False-positive errors | ≤ 3 |
| 3 | Temporal 90° outer point | must be correctly seen |
| 4 | Horizontal ±10° band | < 3 consecutive unseen points |
| 5 | Nasal 60° edge (4 points) | ≥ 1 correctly seen |
| 6 | If fixation loss ≥ 2 **or** false positive ≥ 2 | nasal 60° edge needs ≥ 2 correctly seen |

The overall result is **PASS only when all six criteria are met**.

> **Disclaimer.** This software is a research / decision-support tool. It is not a
> certified medical device. The final fitness decision rests with the examining
> physician.

---

## Repository structure

```
VF-DriverFitness-Analyzer/
├── app.py                      # GUI entry point (python app.py)
├── analyze.py                  # command-line interface
├── requirements.txt
├── LICENSE                     # MIT
├── README.md
├── visual_field_analyzer/      # the core package
│   ├── __init__.py
│   ├── point_grid.py           # 99-point standard test grid (OS/OD)
│   ├── pdf_parser.py           # native-vector PDF parsing + point-state detection
│   ├── engine.py               # six-rule fitness engine
│   ├── report_generator.py     # bilingual A4 HTML report
│   └── main.py                 # tkinter GUI (class VisualFieldAnalyzerApp)
├── sample_data/                # de-identified SYNTHETIC sample PDFs
│   ├── sample_OS.pdf
│   ├── sample_OD.pdf
│   └── README.md
└── tests/
    ├── make_sample_pdf.py      # synthetic ZEISS-like PDF generator
    └── test_pipeline.py        # end-to-end + unit tests
```

## Installation

Requires **Python 3.8+**.

```bash
pip install -r requirements.txt
```

`tkinter` (the GUI toolkit) ships with Python on Windows and macOS. On Linux
install the system package (`python3-tk` / `python3-tkinter`).

## Usage

### GUI

```bash
python app.py
```

Import a ZEISS Humphrey driver's-license PDF, review / correct the auto-detected
points, and click **生成A4报告 (Generate A4 report)**.

### Command line

```bash
# print the verdict
python analyze.py sample_data/sample_OS.pdf

# English output + write an A4 HTML report
python analyze.py path/to/report.pdf --lang en --report-out out/
```

### As a library

```python
from visual_field_analyzer.pdf_parser import parse_pdf
from visual_field_analyzer.engine import analyze

rep = parse_pdf("report.pdf")
states = [1 if s == 1 else 0 for s in (rep.point_states or [1] * 99)]
result = analyze(rep.eye, states, rep.fixation_loss,
                 rep.false_positive, rep.false_negative)
print(result.summary)          # PASS / FAIL with violated rules
```

### Tests

The tests need **no patient data** — they synthesize ZEISS-like PDFs on the fly.

```bash
python tests/test_pipeline.py    # standalone
pytest tests/test_pipeline.py    # or with pytest
```

## How the vector parser works (brief)

1. `page.get_drawings()` returns every vector primitive on the report page.
2. **Fixation & scale.** Gray, unfilled concentric circles (fixation point + 9
   rings of 10°) give the centre `(fx, fy)` and the pixels-per-degree scale
   `ppd = R_max / 9`.
3. **Symbols.** White-filled black-stroked circles → *seen*; black-filled squares
   → *unseen*.
4. **Matching.** Each canonical grid point `(gx, gy)` maps to
   `px = fx + gx/10·ppd`, `py = fy − gy/10·ppd`; a greedy nearest-symbol
   assignment recovers the 99-point state vector.

See [`visual_field_analyzer/pdf_parser.py`](visual_field_analyzer/pdf_parser.py)
for the implementation and
[`tests/make_sample_pdf.py`](tests/make_sample_pdf.py) for a faithful
re-creation of the vector format.

## License

Released under the [MIT License](LICENSE). (The underlying method has been filed
as a Chinese invention patent application; the license governs the **code** only
and does not affect patent rights.)

## Citation

If you use this code, please cite the accompanying TVST article (citation to be
finalised upon acceptance).
