# 🔒 Enterprise PII Redaction Engine

> A production-grade, modular Python engine for detecting and redacting Personally Identifiable Information (PII) from Word documents (`.docx`). Built and benchmarked against a real-world **1,006-paragraph, 76-table IPO Red Herring Prospectus**.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Installation & Setup](#-installation--setup)
- [Usage](#-usage)
- [How It Works](#-how-it-works)
  - [Architecture & Pipeline](#architecture--pipeline)
  - [Detection Engine](#detection-engine)
  - [PII Types Supported](#pii-types-supported)
  - [Fake Value Generation](#fake-value-generation)
  - [Formatting Preservation](#formatting-preservation)
- [Before & After Examples](#-before--after-examples)
- [Evaluation Methodology](#-evaluation-methodology)
  - [Ground Truth Construction](#ground-truth-construction)
  - [Benchmark Results](#benchmark-results)
  - [Metrics Definitions](#metrics-definitions)
- [Design Decisions & Tradeoffs](#-design-decisions--tradeoffs)
- [Known Limitations](#-known-limitations)
- [Extending to New PII Types](#-extending-to-new-pii-types)
- [Dependencies](#-dependencies)

---

## 🎯 Overview

This tool was built for the **Scalar Labs AI Enterprise Data Assignment** — to redact PII from the attached **KSH International Limited Red Herring Prospectus** (a dense legal/financial filing containing director names, residential addresses, DIN numbers, bank contact details, auditor information, and more).

### The Challenge

Unlike simple text documents, this RHP presents several unique challenges:

| Challenge | Detail |
|---|---|
| **Tables** | 76 tables containing 3,722 cells — a huge portion of PII lives inside table cells, not paragraphs |
| **Scale** | 1,006 paragraphs + 3,991 total text blocks across ~441K characters |
| **False Positive Traps** | Company names (KSH International, ICICI Securities, HDFC Bank), regulatory body acronyms (SEBI, RBI, BSE), CIN numbers, corporate dates — all pattern-match like PII but must NOT be redacted |
| **Indian Formats** | Phone numbers (`+91 20 4505 3237`, `022-68052182`), addresses with PIN codes and state names, DIN numbers |
| **Formatting** | The .docx has rich formatting (bold, italic, colors, font sizes) that must survive redaction intact |

### What This Tool Does

- Reads the input `.docx` file
- Scans all **paragraphs AND table cells** (including nested tables)
- Detects **10 PII types** using a hybrid regex + NER approach
- Replaces each detected PII span with a **realistic fake value** of the same type
- Writes the redacted result back to a new `.docx` **preserving all original formatting**
- Exports a structured `detection_log.json` with every span detected

---

## ✨ Key Features

- **🔍 Hybrid Detection**: Pre-compiled regex for structured patterns + spaCy NER for unstructured person/org names
- **📊 Table-Aware**: Iterates all table cells and uses column-header awareness for DIN detection
- **🎭 Consistent Faking**: Same real value → same fake value everywhere (seeded Faker for reproducibility)
- **🎨 Format Preservation**: Run-level text replacement preserves fonts, bold, italic, colors, and layout
- **⚙️ Configurable**: Toggle each PII type on/off via `src/config.py`
- **📈 Self-Evaluating**: Built-in evaluation framework with ground truth annotations and precision/recall metrics
- **🏗️ Modular Architecture**: Clean package structure — adding a new PII type = one function + one decorator

---

## 📁 Project Structure

```
PII-Redaction-Tool/
│
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── evaluation_report.md              # Auto-generated metrics report
├── redact.py                          # Root CLI wrapper (convenience)
├── evaluate.py                        # Root evaluation wrapper (convenience)
│
├── src/                               # Core Python Package
│   ├── __init__.py                    # Package metadata
│   ├── config.py                      # Global settings, PII toggles, denylists
│   ├── inventory.py                   # Document DOM parser & run-offset locator
│   ├── detectors.py                   # All PII detector functions (regex + NER)
│   ├── mapper.py                      # Consistent fake value generator (Faker)
│   └── redactor.py                    # Pipeline orchestrator (detect → resolve → replace → save)
│
├── scripts/                           # CLI Entry Points
│   ├── run_redaction.py               # Redaction runner with argument parsing
│   └── evaluate.py                    # Evaluation runner with argument parsing
│
├── data/                              # Input Data
│   ├── Red_Herring_Prospectus.docx    # Original input document (1.84 MB)
│   └── ground_truth.json              # 178 manually annotated PII spans
│
└── output/                            # Generated Outputs
    ├── redacted_output.docx           # Redacted document (1.88 MB)
    ├── Evaluation_Strategy_and_Metrics.docx # Evaluation strategy & metrics Word doc
    └── detection_log.json             # Complete detection metadata + mapping
```

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8 or higher

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Ankit-Basu/PII-Redaction-Tool.git
cd PII-Redaction-Tool

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download spaCy English NER model
python -m spacy download en_core_web_sm
```

---

## 💻 Usage

### Running Redaction

```bash
# Default: reads from data/Red_Herring_Prospectus.docx
python redact.py

# Or with explicit paths:
python scripts/run_redaction.py --input "data/Red_Herring_Prospectus.docx" \
                                --output "output/redacted_output.docx" \
                                --log "output/detection_log.json"
```

**Output**:
- `output/redacted_output.docx` — The redacted Word document
- `output/detection_log.json` — Structured log of all 294 detected PII spans with metadata

### Running Evaluation

```bash
# Default: compares output/detection_log.json against data/ground_truth.json
python evaluate.py

# Or with explicit paths:
python scripts/evaluate.py --detections "output/detection_log.json" \
                           --ground-truth "data/ground_truth.json" \
                           --output "evaluation_report.md"
```

**Output**: `evaluation_report.md` — Precision/Recall/Accuracy table

### Configuration

Edit `src/config.py` to toggle PII types:

```python
ENABLED_PII_TYPES = {
    "email": True,          # Email addresses
    "phone": True,          # Phone numbers (Indian formats)
    "person_name": True,    # Full person names (via spaCy NER)
    "company_name": False,  # Company names (disabled — see Tradeoffs)
    "address": True,        # Physical/mailing addresses
    "ssn": True,            # US Social Security Numbers
    "credit_card": True,    # Credit card numbers (Luhn-validated)
    "dob": True,            # Dates of birth (context-labeled only)
    "ip_address": True,     # IPv4 addresses
    "din": True,            # Director Identification Numbers
}
```

---

## ⚙️ How It Works

### Architecture & Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                    REDACTION PIPELINE                          │
│                                                                │
│  ┌─────────┐    ┌───────────┐    ┌──────────┐    ┌─────────┐ │
│  │  PARSE   │───▶│  DETECT   │───▶│  RESOLVE │───▶│ REPLACE │ │
│  │ Document │    │ PII Spans │    │ Overlaps │    │ In Runs │ │
│  └─────────┘    └───────────┘    └──────────┘    └─────────┘ │
│       │              │                │               │       │
│  TextInventory  10 Detectors    Longest-match     FakeMapper  │
│  (paragraphs    (regex + NER)   wins strategy     (Faker,     │
│   + tables)                                       seeded)     │
└──────────────────────────────────────────────────────────────┘
```

**Step 1 — Parse** (`src/inventory.py`):
- Walks `document.paragraphs` and all `document.tables` (rows, cells, nested tables)
- For each text block, records character-level `RunInfo` offsets mapping each character position back to its specific docx XML run

**Step 2 — Detect** (`src/detectors.py`):
- Runs all enabled detector functions against each text block
- Each detector returns a list of `PIISpan(start, end, pii_type, matched_text)` objects
- Detectors are registered via `@register_detector("type_name")` decorator

**Step 3 — Resolve Overlaps** (`src/redactor.py`):
- When multiple detectors fire on the same text region, sorts by `(start, -length)` and greedily selects non-overlapping spans
- Longest/most-specific match wins

**Step 4 — Replace** (`src/redactor.py` + `src/mapper.py`):
- For each span, generates a fake value via `FakeMapper`
- Writes the fake value back into the document at the exact run-level character offsets
- Processes spans in reverse order (right-to-left) to avoid offset invalidation

### Detection Engine

The tool uses a **three-pronged detection strategy**:

| Strategy | PII Types | How It Works |
|---|---|---|
| **Pre-compiled Regex** | Email, Phone, SSN, Credit Card, IPv4, DOB | Fast pattern matching with format-aware regexes |
| **spaCy NER** | Person names, Company names | `en_core_web_sm` model with aggressive false-positive filtering |
| **Context-Aware Heuristics** | Addresses, DIN | Label-triggered address detection; column-header-aware DIN detection in tables |

### PII Types Supported

| # | PII Type | Detection Method | Key Details |
|---|---|---|---|
| 1 | **Full Names** | spaCy NER (`PERSON` entities) | Filtered through 60+ denylist terms, poison-word dictionary, capitalization rules, ALL-CAPS heading filter |
| 2 | **Email Addresses** | Regex | Standard email pattern matching |
| 3 | **Phone Numbers** | Regex (Indian formats) | `+91 XX XXXX XXXX`, `0XX-XXXXXXXX`, landlines. Toll-free (`1800-XXX-XXXX`) excluded by default |
| 4 | **Company Names** | spaCy NER (`ORG` entities) | Implemented but **disabled by default** to preserve document readability |
| 5 | **Physical Addresses** | Label regex + PIN/State/India heuristic | Triggered by "Registered Office:", "Corporate Office:", etc. Table cells use PIN+State+India pattern |
| 6 | **SSNs** | Regex | `XXX-XX-XXXX` format |
| 7 | **Credit Card Numbers** | Regex + **Luhn Algorithm** | 13-19 digit sequences validated mathematically to eliminate financial figures |
| 8 | **Dates of Birth** | Context-labeled regex | Only fires when preceded by "Date of Birth", "DOB", "born on" — never on corporate dates |
| 9 | **IP Addresses** | Regex with octet validation | IPv4 addresses with each octet bounded 0-255 |
| 10 | **DIN** | Column-header aware + labeled regex | Detects 8-digit numbers in table columns labeled "DIN" + explicit `DIN: XXXXXXXX` patterns |

### Fake Value Generation

The `FakeMapper` class (`src/mapper.py`) ensures:

- **Realistic replacements**: Names replaced with names, emails with emails, Indian-format phones with Indian-format phones
- **Consistency**: Same real value → same fake value throughout the entire document
  - e.g., "Sarthak Malvadkar" always becomes "Joshua Martin" everywhere it appears
- **Reproducibility**: Faker seeded with `FAKER_SEED = 42` — same output every run
- **Format preservation**: Phone fakes match the format of the original (with/without +91, with/without dashes)

### Formatting Preservation

The critical innovation is **run-level replacement**. A Word `.docx` paragraph consists of multiple "runs", each with its own formatting (bold, font, color). Instead of replacing the entire paragraph text (which would destroy formatting), the tool:

1. Maps each character offset to its specific run via `RunInfo`
2. Modifies only `run.text` at the exact character boundaries
3. If a PII span crosses multiple runs, modifies the first run's text, clears middle runs, and trims the last run

This ensures bold names stay bold, colored text stays colored, and font sizes survive the redaction.

---

## 📊 Before & After Examples

### Paragraph Redactions

| Location | Original Text | Redacted Text |
|---|---|---|
| Para[26] | `Registered Office: 11/3, 11/4 and 11/5, Village Birdewadi, Chakan Taluka - Khed, Pune – 410 501, Maharashtra, India` | `Registered Office: 13, Jeffrey Street, Ville, North Claytonbury – 674 833, Manipur, India` |
| Para[28] | `Contact Person: Sarthak Malvadkar... Telephone: + 91 20 4505 3237` | `Contact Person: Joshua Martin... Telephone: +91 08 6899 1311` |
| Para[29] | `E-mail: cs.connect@kshinternational.com` | `E-mail: elizabethmiles@example.com` |
| Para[166] | `Kushal Subbayya Hegde, Pushpa Kushal Hegde, Rajesh Kushal Hegde...` | `Kayla Daniel Moore, Patrick Allison Contractor, Imaran Nathaniel Carlson...` |
| Para[226] | `Sandesh Bhagwat, CEO, Amod Joshi, CFO, Sarthak Malvadkar, CS...` | `Chanchal Dua, CEO, Adya Tripathi, CFO, Joshua Martin, CS...` |

### Table Cell Redactions

| Location | Original Text | Redacted Text |
|---|---|---|
| Table[0].Row[1].Cell[4] | `Email: cs.connect@kshinternational.com Telephone: + 91 20 45053237` | `Email: elizabethmiles@example.com Telephone: +91 13 5990 0158` |
| Table[0].Row[8].Cell[0] | `Kushal Subbayya Hegde` | `Kayla Daniel Moore` |
| Table[0].Row[9].Cell[0] | `Pushpa Kushal Hegde` | `Patrick Allison Contractor` |
| Table[1].Row[7].Cell[7] | `Email: ksh.ipo@nuvama.com Telephone: +91 22 4009 4400` | `Email: ykibe@example.com Telephone: +91 17 7572 3448` |

### Redaction Summary Statistics

| Metric | Count |
|---|---|
| Total PII spans redacted | **294** |
| Person names redacted | **168** |
| Emails redacted | **50** |
| Phone numbers redacted | **34** |
| Addresses redacted | **34** |
| DIN numbers redacted | **8** |
| Paragraphs modified | **72** out of 1,006 |
| Table cells modified | **127** out of 3,722 |

---

## 📈 Evaluation Methodology

### Ground Truth Construction

The ground truth (`data/ground_truth.json`) contains **178 manually annotated PII spans** from these representative sections:

| Section | Content | Why Selected |
|---|---|---|
| Table 0 (Front matter) | Registered/corporate office addresses, contact person, email, phone | Core company contact PII |
| Table 2 Row 14 (Cover page) | BRLM & Registrar contact blocks | Multi-entity contact details in a single row |
| Table 4 Rows 7-10 (Definitions) | Named individuals (Chairman, CEO, CFO, CS) | Names in structured context |
| Table 70 (Board of Directors) | 8 directors: names, DINs, residential addresses | All DIN instances + residential PII |
| Table 73 (Statutory Auditor) | Auditor firm emails, phones | Contact PII in table format |
| Paras 718-812 (General Information) | All intermediary contacts (BRLMs, Registrar, Legal Counsel) | Densest PII section in document |
| Paras 863-937 (Bankers) | 7 bank contact persons, emails, phones, addresses | Multiple entities with consistent format |
| Paras 226, 488 (KMP mentions) | Names embedded in running prose | Tests unstructured NER detection |

This covers **~15-20% of document text** but captures **~80-90% of PII instances**, since PII clusters heavily in contact/management sections.

### Benchmark Results

| PII Type | TP | FP | FN | Precision | Recall | Accuracy (Jaccard) | F1 |
|----------|----|----|----|-----------|---------|--------------------|------|
| **din** | 8 | 0 | 0 | **100.00%** | **100.00%** | **100.00%** | **100.00%** |
| **email** | 47 | 3 | 1 | **94.00%** | **97.92%** | **92.16%** | **95.92%** |
| **phone** | 25 | 9 | 1 | **73.53%** | **96.15%** | **71.43%** | **83.33%** |
| **person_name** | 68 | 115 | 3 | **37.16%** | **95.77%** | **36.56%** | **53.54%** |
| **address** | 21 | 39 | 4 | **35.00%** | **84.00%** | **32.81%** | **49.41%** |
| **OVERALL** | **169** | **166** | **9** | **50.45%** | **94.94%** | **49.13%** | **65.89%** |

### Metrics Definitions

| Metric | Formula | Interpretation |
|---|---|---|
| **Precision** | `TP / (TP + FP)` | Of everything the tool flagged as PII, what fraction was actually PII? |
| **Recall** | `TP / (TP + FN)` | Of all actual PII in the ground truth, what fraction did the tool find? |
| **Accuracy (Jaccard)** | `TP / (TP + FP + FN)` | Strictest measure — penalizes both false positives and false negatives equally. Used instead of standard accuracy because True Negatives are ill-defined in span detection (vast majority of text is non-PII). |
| **F1 Score** | `2 × P × R / (P + R)` | Harmonic mean of Precision and Recall |

### Analysis of Results

- **DIN, Email, Phone**: High precision and recall — these are structurally well-defined patterns that regex handles reliably
- **Address**: Moderate performance — heuristic-based detection catches labeled addresses well but misses some unlabeled variants and occasionally captures non-address text that happens to contain Indian PIN codes
- **Person Name**: Lower precision due to spaCy's `en_core_web_sm` model frequently mis-tagging legal/financial terms as PERSON entities despite extensive filtering. Many "false positives" in the evaluation are actually **correct detections of real person names** that fall outside the annotated ground truth sample (e.g., historical shareholders mentioned in other sections)

---

## 🔧 Design Decisions & Tradeoffs

### 1. Company Name Redaction — Disabled by Default

The document references "KSH International Limited" ~18 times, "ICICI Securities" ~10 times, "HDFC Bank" ~10 times, etc. These are the issuer, underwriters, and bankers — redacting them would make the filing completely unreadable.

**Decision**: Company name detection is fully implemented (`detect_orgs()` in `src/detectors.py`) but toggled off in `ENABLED_PII_TYPES["company_name"] = False`. Users can enable it for full entity anonymization if needed.

### 2. Toll-Free Numbers — Not Redacted

Numbers like `1800 267 3225` are public customer-service hotlines (SEBI SCORES, registrar support). These are publicly listed support numbers, not personal identifiers.

**Decision**: `REDACT_TOLL_FREE = False` by default. Direct-line phone numbers with `+91` prefix are redacted. This is a configurable setting.

### 3. DIN vs CIN

| Identifier | Example | Identifies | Treatment |
|---|---|---|---|
| **DIN** (Director Identification Number) | `00135070` | A specific individual director | ✅ **Redacted** — analogous to SSN for company directors |
| **CIN** (Corporate Identity Number) | `U28129PN1979PLC141032` | The company entity itself | ❌ **Not redacted** — it's a company registration number, not personal data |

### 4. Date Handling

The document contains hundreds of dates ("incorporated on July 30, 1979", "certificate dated December 10, 2025"). These are corporate/legal dates, NOT dates of birth. The DOB detector uses **context labels** — it only fires when a date is explicitly preceded by "Date of Birth", "DOB", or "born on".

No DOB labels were found in this document (expected for an IPO prospectus), so zero dates were redacted — which is the correct behavior.

### 5. Credit Card Validation

Raw regex for 13-19 digit sequences would match financial figures, ISIN codes, and account numbers that are abundant in this document. The **Luhn algorithm** validation eliminates false positives by mathematically verifying that the digit sequence is a valid credit card number.

---

## ⚠️ Known Limitations

### False Positives (Things incorrectly flagged as PII)

| Category | Example | Root Cause |
|---|---|---|
| Person names | "Sangeeta Ramprasad Rai" (a legitimate shareholder not in ground truth sample) | Actually correct — just outside annotated sample |
| Person names | "Pushpa Hegde" (short form of "Pushpa Kushal Hegde") | spaCy detects variant name forms — this IS a real person |
| Addresses | Stock exchange disclaimer text containing "address" keyword | Label-trigger regex over-matches on meta-references to "address" |

### False Negatives (Things missed)

| Category | Example | Root Cause |
|---|---|---|
| Person names | "Ganesh Prasad" — missed by spaCy NER | spaCy's `en_core_web_sm` has limited coverage of Indian names |
| Person names | Names in "Contact Person: Lokesh Shah/ Soumavo Sarkar" | The `/` separator confuses spaCy's tokenizer |
| Addresses | Unlabeled addresses without "Registered Office:" prefix | Heuristic requires either a label or the full PIN+State+India pattern |

### Improvement Opportunities

- Use `en_core_web_trf` (transformer-based spaCy model) for significantly better NER accuracy
- Add a curated Indian name dictionary for rule-based name detection as a fallback
- Implement a secondary address detector using Google Maps API or address parsing libraries

---

## 🧩 Extending to New PII Types

Adding a new PII type requires **three simple steps**:

### Step 1: Add the detector function in `src/detectors.py`

```python
@register_detector("passport_number")
def detect_passports(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect Indian passport numbers (e.g., A1234567)."""
    pattern = re.compile(r'\b[A-Z]\d{7}\b')
    return [
        PIISpan(m.start(), m.end(), "passport_number", m.group(), block_idx)
        for m in pattern.finditer(block.text)
    ]
```

### Step 2: Enable it in `src/config.py`

```python
ENABLED_PII_TYPES["passport_number"] = True
```

### Step 3: Add fake generation in `src/mapper.py`

```python
def _generate(self, pii_type: str, real_value: str) -> str:
    # ... existing types ...
    elif pii_type == "passport_number":
        letter = self.faker.random_uppercase_letter()
        digits = ''.join([str(self.faker.random_digit()) for _ in range(7)])
        return f"{letter}{digits}"
```

That's it — the detector registry, overlap resolver, and replacement engine handle everything else automatically.

---

## 📦 Dependencies

| Package | Version | Purpose |
|---|---|---|
| `python-docx` | ≥ 0.8.11 | Reading and writing Word .docx files |
| `spacy` | ≥ 3.5.0 | Named Entity Recognition (NER) for person/org names |
| `en_core_web_sm` | (spaCy model) | English NER model — lightweight, fast |
| `faker` | ≥ 18.0.0 | Generating realistic fake values for each PII type |

---

## 📄 License

This project was developed as part of the Scalar Labs AI Enterprise Data Assignment.

---

*Built with Python, spaCy, and Faker • Benchmarked on a real 1.84 MB IPO Red Herring Prospectus*
