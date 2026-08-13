# -*- coding: utf-8 -*-
"""Central Redactor engine orchestrating detection, overlap resolution, and docx replacement."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import docx
from docx.document import Document
from docx.text.paragraph import Paragraph

from src.config import ENABLED_PII_TYPES
from src.detectors import DETECTORS
from src.inventory import CellLocation, PIISpan, TextBlock, TextInventory
from src.mapper import FakeMapper

log = logging.getLogger("pii_redactor")

_DIN_COLUMN_RE = re.compile(r'\b\d{8}\b')


class Redactor:
    """Central PII Redaction Engine."""

    def __init__(
        self,
        input_path: str,
        output_path: str,
        log_path: str = "output/detection_log.json",
    ) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.log_path = log_path
        self.doc: Document = docx.Document(input_path)
        self.inventory: TextInventory = TextInventory(self.doc)
        self.mapper = FakeMapper()
        self.all_spans: List[PIISpan] = []
        self._table_din_columns: Dict[int, Set[int]] = {}
        self._table_name_columns: Dict[int, Set[int]] = {}

    def run(self) -> None:
        """Execute complete redaction pipeline."""
        log.info(f"Loaded document: {self.input_path}")
        log.info(f"Text Inventory: {len(self.inventory.blocks)} blocks")

        self._identify_columns()
        self._detect_all()
        self._resolve_overlaps()
        self._apply_replacements()
        self._save()
        self._export_log()

    def _identify_columns(self) -> None:
        """Identify table columns with 'DIN' or 'Name' headers."""
        for t_idx, table in enumerate(self.doc.tables):
            if not table.rows:
                continue
            header_row = table.rows[0]
            din_cols: Set[int] = set()
            name_cols: Set[int] = set()
            for c_idx, cell in enumerate(header_row.cells):
                txt = cell.text.strip().upper()
                if 'DIN' in txt:
                    din_cols.add(c_idx)
                if txt in ['NAME', 'NAME OF DIRECTOR', 'NAME OF THE DIRECTOR', 'NAME OF PROMOTER', 'NAME OF THE PROMOTER', 'DIRECTOR NAME']:
                    name_cols.add(c_idx)
            if din_cols:
                self._table_din_columns[t_idx] = din_cols
                log.info(f"Table {t_idx}: DIN column(s) at indices {din_cols}")
            if name_cols:
                self._table_name_columns[t_idx] = name_cols
                log.info(f"Table {t_idx}: Name column(s) at indices {name_cols}")

    def _detect_all(self) -> None:
        """Run all active detectors over all blocks."""
        total_spans = 0
        for block_idx, block in enumerate(self.inventory.blocks):
            block_spans: List[PIISpan] = []

            for pii_type, detector_func in DETECTORS.items():
                if not ENABLED_PII_TYPES.get(pii_type, False):
                    continue
                spans = detector_func(block, block_idx)
                block_spans.extend(spans)

            if ENABLED_PII_TYPES.get("din", False):
                block_spans.extend(self._detect_din_in_table_context(block, block_idx))

            if ENABLED_PII_TYPES.get("person_name", False):
                block_spans.extend(self._detect_names_in_table_context(block, block_idx))

            self.all_spans.extend(block_spans)
            total_spans += len(block_spans)

        log.info(f"Total raw PII spans detected: {total_spans}")

    def _detect_din_in_table_context(self, block: TextBlock, block_idx: int) -> List[PIISpan]:
        """Detect bare 8-digit DIN numbers under DIN headers."""
        spans: List[PIISpan] = []
        loc = block.location
        if not isinstance(loc, CellLocation):
            return spans

        t_idx = loc.table_idx
        c_idx = loc.cell_idx
        if t_idx in self._table_din_columns and c_idx in self._table_din_columns[t_idx]:
            for m in _DIN_COLUMN_RE.finditer(block.text):
                already_found = any(
                    s.start == m.start() and s.end == m.end() and s.block_index == block_idx
                    for s in self.all_spans
                )
                if not already_found:
                    spans.append(PIISpan(m.start(), m.end(), "din", m.group(), block_idx))
        return spans

    def _detect_names_in_table_context(self, block: TextBlock, block_idx: int) -> List[PIISpan]:
        """Detect person names under table Name headers."""
        spans: List[PIISpan] = []
        loc = block.location
        if not isinstance(loc, CellLocation) or loc.row_idx == 0:
            return spans

        t_idx = loc.table_idx
        c_idx = loc.cell_idx
        if t_idx in self._table_name_columns and c_idx in self._table_name_columns[t_idx]:
            text = block.text.strip().rstrip('*')
            words = text.split()
            # If cell text is a 2-4 word capitalized person name
            if 2 <= len(words) <= 5 and all(w[0].isupper() or w in ['N.', 'B.', 'K.'] for w in words if len(w) > 0):
                clean_text = ' '.join(words)
                already = any(
                    s.block_index == block_idx
                    for s in self.all_spans
                )
                if not already:
                    spans.append(PIISpan(0, len(block.text), "person_name", block.text, block_idx))
        return spans

    def _resolve_overlaps(self) -> None:
        """Resolve overlapping spans: longest match wins."""
        spans_by_block: Dict[int, List[PIISpan]] = {}
        for span in self.all_spans:
            spans_by_block.setdefault(span.block_index, []).append(span)

        resolved: List[PIISpan] = []
        for block_idx, spans in spans_by_block.items():
            spans.sort(key=lambda s: (s.start, -(s.end - s.start)))
            accepted: List[PIISpan] = []
            for span in spans:
                if not any(span.start < ex.end and span.end > ex.start for ex in accepted):
                    accepted.append(span)
            resolved.extend(accepted)

        log.info(f"Overlap resolution: {len(self.all_spans)} -> {len(resolved)} spans")
        self.all_spans = resolved

    def _apply_replacements(self) -> None:
        """Apply fake-value replacements back into the document runs in-place."""
        spans_by_block: Dict[int, List[PIISpan]] = {}
        for span in self.all_spans:
            spans_by_block.setdefault(span.block_index, []).append(span)

        replaced_count = 0
        for block_idx, spans in spans_by_block.items():
            block = self.inventory.blocks[block_idx]
            para = block.paragraph_ref
            if para is None:
                continue

            spans.sort(key=lambda s: s.start, reverse=True)
            for span in spans:
                fake_val = self.mapper.get_fake(span.pii_type, span.matched_text)
                self._replace_in_runs(para, span.start, span.end, fake_val)
                replaced_count += 1

        log.info(f"Applied {replaced_count} replacements")

    @staticmethod
    def _replace_in_runs(para: Paragraph, start: int, end: int, replacement: str) -> None:
        """Replace text inside runs at character boundaries to preserve styles."""
        runs = para.runs
        if not runs:
            return

        run_boundaries: List[Tuple[int, int, int]] = []
        offset = 0
        for i, run in enumerate(runs):
            rlen = len(run.text)
            run_boundaries.append((offset, offset + rlen, i))
            offset += rlen

        affected = [(b_start, b_end, r_idx) for b_start, b_end, r_idx in run_boundaries if b_start < end and b_end > start]
        if not affected:
            return

        if len(affected) == 1:
            rb_start, _, r_idx = affected[0]
            run = runs[r_idx]
            l_start = start - rb_start
            l_end = end - rb_start
            run.text = run.text[:l_start] + replacement + run.text[l_end:]
        else:
            f_start, _, f_idx = affected[0]
            l_start, _, l_idx = affected[-1]
            first_run = runs[f_idx]
            last_run = runs[l_idx]

            first_run.text = first_run.text[:start - f_start] + replacement
            last_run.text = last_run.text[end - l_start:]

            for _, _, r_idx in affected[1:-1]:
                runs[r_idx].text = ""

    def _save(self) -> None:
        """Save redacted docx."""
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(self.output_path)
        log.info(f"Saved redacted document: {self.output_path}")

    def _export_log(self) -> None:
        """Export detection log metadata."""
        log_data = {
            "total_spans": len(self.all_spans),
            "spans_by_type": {},
            "spans": [],
            "mapping": self.mapper.get_mapping(),
        }

        type_counts: Dict[str, int] = {}
        for span in self.all_spans:
            type_counts[span.pii_type] = type_counts.get(span.pii_type, 0) + 1
            span_dict = span.to_dict()
            block = self.inventory.blocks[span.block_index]
            span_dict["location"] = repr(block.location)
            log_data["spans"].append(span_dict)

        log_data["spans_by_type"] = type_counts
        log_file = Path(self.log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        log.info(f"Exported detection log: {log_file}")
