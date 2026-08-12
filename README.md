# Enterprise PII Redaction Engine

A production-grade, modular Python engine designed for detecting and redacting Personally Identifiable Information (PII) from Word documents (`.docx`). Built and benchmarked specifically for large Indian corporate filings (IPO Red Herring Prospectuses).

---

## Project Structure

```
d:\Scalar labs ai\
├── README.md                          # Project documentation
├── requirements.txt                   # Dependency requirements
├── evaluation_report.md              # Evaluation metrics report
├── redact.py                          # Root CLI wrapper
├── evaluate.py                        # Root evaluation wrapper
├── src/                               # Modular Python Package
│   ├── __init__.py
│   ├── config.py                      # Config settings & PII toggles
│   ├── inventory.py                   # Document DOM parser & run offset locator
│   ├── detectors.py                   # Modular regex + spaCy NER detectors
│   ├── mapper.py                      # Consistent fake value generator (Faker)
│   └── redactor.py                    # Redactor pipeline orchestrator
├── data/
│   ├── Red_Herring_Prospectus.docx    # Input document
│   └── ground_truth.json              # Benchmark ground truth spans
├── output/
│   ├── redacted_output.docx           # Final redacted document
│   └── detection_log.json             # Detection metadata log
├── scripts/
│   ├── run_redaction.py               # CLI runner script
│   └── evaluate.py                    # Evaluation runner script
└── scratch/                           # Analysis & inspection logs
```

---

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### 2. Running Redaction

To redact the document:

```bash
python scripts/run_redaction.py
# or simply:
python redact.py
```

Outputs are saved in:
- `output/redacted_output.docx`: Final redacted document
- `output/detection_log.json`: Structured log of detected spans and mapping

### 3. Running Evaluation

To evaluate detection metrics against benchmark ground truth:

```bash
python scripts/evaluate.py
# or simply:
python evaluate.py
```

Outputs:
- `evaluation_report.md`: Summary table of TP, FP, FN, Precision, Recall, Accuracy (Jaccard), and F1 per PII type.

---

## Architecture & Features

1. **Paragraph & Table Traversals (`src/inventory.py`)**:
   - Walks all document paragraphs and table cells (including nested tables).
   - Character-level `RunInfo` tracking ensures replacements occur directly in `run.text`, preserving original styling, fonts, and bolding.

2. **Hybrid Detection Engine (`src/detectors.py`)**:
   - **Regex**: Email, Phone numbers (Indian `+91`, landline STD, toll-free), US SSN, IPv4, Credit Cards with **Luhn Algorithm Validation**.
   - **Context-Aware**: Column-header aware Director Identification Numbers (**DIN**), explicit **DOB** labels.
   - **Heuristic**: Multi-line physical address matching for Registered/Corporate offices.
   - **spaCy NER**: Filtered `PERSON` entity detection with aggressive false-positive guards (denylist, poison words, capitalization rules).

3. **Consistent Anonymization (`src/mapper.py`)**:
   - Uses `Faker` seeded with `FAKER_SEED = 42`.
   - Maintains a deterministic mapping dictionary per PII type to guarantee the same real value is replaced by the exact same fake value across the whole document.

---

## Tradeoffs & Design Decisions

- **Company Names (`company_name`)**: Detection exists but is disabled by default (`ENABLED_PII_TYPES["company_name"] = False`) to prevent altering legal party names which would make the filing unreadable.
- **Toll-Free Numbers**: Customer care lines (`1800-XXX-XXXX`) are public support lines and are excluded from redaction by default (`REDACT_TOLL_FREE = False`).
- **DIN vs. CIN**: DIN (Director Identification Number) identifies an individual director and is redacted. CIN (Corporate Identity Number) identifies the corporate entity and is preserved.

---

## Verification & Metrics

The tool achieves high precision and recall on structured PII identifiers:
- **DIN**: 100% Precision, 100% Recall, 100% Accuracy
- **Email**: 94% Precision, 98% Recall, 92% Accuracy
- **Phone**: 74% Precision, 96% Recall, 71% Accuracy
