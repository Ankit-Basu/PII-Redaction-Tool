# PII Redaction — Evaluation Report

## Methodology

Ground truth was manually annotated from representative PII-dense sections of the KSH International Limited Red Herring Prospectus (~15-20% of document text, covering ~80-90% of PII instances).

**Accuracy formula**: Jaccard index = `TP / (TP + FP + FN)`.

## Benchmark Results

| PII Type | TP | FP | FN | Precision | Recall | Accuracy (Jaccard) | F1 |
|----------|----|----|----|-----------|---------|--------------------|------|
| address | 21 | 39 | 4 | 35.00% | 84.00% | 32.81% | 49.41% |
| din | 8 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| email | 47 | 3 | 1 | 94.00% | 97.92% | 92.16% | 95.92% |
| person_name | 68 | 115 | 3 | 37.16% | 95.77% | 36.56% | 53.54% |
| phone | 25 | 9 | 1 | 73.53% | 96.15% | 71.43% | 83.33% |
| **OVERALL** | **169** | **166** | **9** | **50.45%** | **94.94%** | **49.13%** | **65.89%** |