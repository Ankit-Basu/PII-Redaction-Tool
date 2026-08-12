# PII Redaction — Evaluation Report

## Methodology

Ground truth was manually annotated from representative PII-dense sections of the KSH International Limited Red Herring Prospectus (~15-20% of document text, covering ~80-90% of PII instances).

**Accuracy formula**: Jaccard index = `TP / (TP + FP + FN)`.

## Benchmark Results

| PII Type | TP | FP | FN | Precision | Recall | Accuracy (Jaccard) | F1 |
|----------|----|----|----|-----------|---------|--------------------|------|
| address | 13 | 8 | 12 | 61.90% | 52.00% | 39.39% | 56.52% |
| din | 8 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| email | 47 | 3 | 1 | 94.00% | 97.92% | 92.16% | 95.92% |
| person_name | 32 | 87 | 39 | 26.89% | 45.07% | 20.25% | 33.68% |
| phone | 25 | 9 | 1 | 73.53% | 96.15% | 71.43% | 83.33% |
| **OVERALL** | **125** | **107** | **53** | **53.88%** | **70.22%** | **43.86%** | **60.98%** |