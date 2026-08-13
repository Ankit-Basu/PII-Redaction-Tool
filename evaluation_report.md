# PII Redaction — Evaluation Report

## Methodology

Ground truth was manually annotated from representative PII-dense sections of the KSH International Limited Red Herring Prospectus (~15-20% of document text, covering ~80-90% of PII instances).

**Accuracy formula**: Jaccard index = `TP / (TP + FP + FN)`.

## Benchmark Results

| PII Type | TP | FP | FN | Precision | Recall | Accuracy (Jaccard) | F1 |
|----------|----|----|----|-----------|---------|--------------------|------|
| address | 19 | 15 | 6 | 55.88% | 76.00% | 47.50% | 64.41% |
| din | 8 | 0 | 0 | 100.00% | 100.00% | 100.00% | 100.00% |
| email | 47 | 3 | 1 | 94.00% | 97.92% | 92.16% | 95.92% |
| person_name | 57 | 111 | 14 | 33.93% | 80.28% | 31.32% | 47.70% |
| phone | 25 | 9 | 1 | 73.53% | 96.15% | 71.43% | 83.33% |
| **OVERALL** | **156** | **138** | **22** | **53.06%** | **87.64%** | **49.37%** | **66.10%** |