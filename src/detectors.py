# -*- coding: utf-8 -*-
"""Optimized detector registry and PII detectors (Regex + spaCy NER)."""

from __future__ import annotations

import logging
import re
from typing import Callable, Dict, List, Optional, Set

from src.config import (
    INDIAN_STATES,
    PERSON_DENYLIST,
    REDACT_TOLL_FREE,
    SPACY_MODEL,
)
from src.inventory import CellLocation, PIISpan, TextBlock

try:
    import spacy
    from spacy.language import Language
except ImportError:
    spacy = None  # type: ignore

log = logging.getLogger("pii_redactor")

DetectorFunc = Callable[[TextBlock, int], List[PIISpan]]
DETECTORS: Dict[str, DetectorFunc] = {}


def register_detector(pii_type: str) -> Callable:
    """Decorator to register a PII detector function."""
    def decorator(func: DetectorFunc) -> DetectorFunc:
        DETECTORS[pii_type] = func
        return func
    return decorator


# Pre-compiled Regex Patterns for Maximum Speed
_EMAIL_RE = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
_PHONE_RE = re.compile(
    r'(?:'
    r'(?:\+\s*91[\s-]*(?:\d[\s-]*){10})'
    r'|(?:\+\s*91[\s-]*(?:\d[\s-]*){7,8})'
    r'|(?:0\d{2,3}[\s-]*\d{7,8})'
    r')',
    re.IGNORECASE,
)
_TOLL_FREE_RE = re.compile(r'1800[\s-]*\d{3}[\s-]*\d{3,4}')
_SSN_RE = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
_CC_RE = re.compile(r'\b(?:\d[\s-]*){13,19}\b')
_IP_RE = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
    r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'
)
_DOB_CONTEXT_RE = re.compile(
    r'(?:date\s+of\s+birth|DOB|born\s+on|d\.o\.b\.?)\s*[:\-]?\s*'
    r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
    re.IGNORECASE,
)
_DIN_LABELED_RE = re.compile(r'\bDIN\s*[:\s]\s*(\d{8})\b', re.IGNORECASE)
_ADDR_LABEL_RE = re.compile(
    r'(?:Registered\s+Office|Corporate\s+Office|Address|Office)\s*[:\-]?\s*',
    re.IGNORECASE,
)
_PIN_CODE_RE = re.compile(r'\b\d{3}\s?\d{3}\b')
_STATE_RE = re.compile(r'\b(?:' + '|'.join(re.escape(s) for s in INDIAN_STATES) + r')\b', re.IGNORECASE)


@register_detector("email")
def detect_emails(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect email addresses via pre-compiled regex."""
    return [
        PIISpan(m.start(), m.end(), "email", m.group(), block_idx)
        for m in _EMAIL_RE.finditer(block.text)
    ]


@register_detector("phone")
def detect_phones(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect Indian format phone numbers."""
    spans: List[PIISpan] = []
    for m in _PHONE_RE.finditer(block.text):
        matched = m.group().strip()
        digits = re.sub(r'\D', '', matched)
        if len(digits) >= 7:
            spans.append(PIISpan(m.start(), m.end(), "phone", matched, block_idx))

    if REDACT_TOLL_FREE:
        for m in _TOLL_FREE_RE.finditer(block.text):
            spans.append(PIISpan(m.start(), m.end(), "phone", m.group(), block_idx))

    return spans


@register_detector("ssn")
def detect_ssns(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect US SSNs."""
    return [
        PIISpan(m.start(), m.end(), "ssn", m.group(), block_idx)
        for m in _SSN_RE.finditer(block.text)
    ]


def _luhn_check(number: str) -> bool:
    """Validate credit card number using Luhn algorithm."""
    digits = [int(d) for d in re.sub(r'\D', '', number)]
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@register_detector("credit_card")
def detect_credit_cards(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect credit card numbers validated with Luhn."""
    spans: List[PIISpan] = []
    for m in _CC_RE.finditer(block.text):
        candidate = m.group().strip()
        digits = re.sub(r'\D', '', candidate)
        if 13 <= len(digits) <= 19 and digits[0] in '3456' and _luhn_check(digits):
            spans.append(PIISpan(m.start(), m.end(), "credit_card", candidate, block_idx))
    return spans


@register_detector("ip_address")
def detect_ips(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect IPv4 addresses."""
    return [
        PIISpan(m.start(), m.end(), "ip_address", m.group(), block_idx)
        for m in _IP_RE.finditer(block.text)
    ]


@register_detector("dob")
def detect_dob(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect explicitly labeled DOBs."""
    return [
        PIISpan(m.start(1), m.end(1), "dob", m.group(1), block_idx)
        for m in _DOB_CONTEXT_RE.finditer(block.text)
    ]


@register_detector("din")
def detect_din(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect labeled Director Identification Numbers."""
    return [
        PIISpan(m.start(1), m.end(1), "din", m.group(1), block_idx)
        for m in _DIN_LABELED_RE.finditer(block.text)
    ]


@register_detector("address")
def detect_addresses(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect mailing and corporate addresses."""
    spans: List[PIISpan] = []
    text = block.text

    # Skip stock exchange website disclaimers that match "address" keywords
    if "websites of the Stock Exchanges" in text:
        return spans

    for label_m in _ADDR_LABEL_RE.finditer(text):
        addr_start = label_m.end()
        rest = text[addr_start:]
        india_m = re.search(r'India\s*[;,.\n]?', rest, re.IGNORECASE)
        if india_m:
            addr_end = addr_start + india_m.end()
            addr_text = text[addr_start:addr_end].strip().rstrip(';,.')
            if len(addr_text) > 15:
                spans.append(PIISpan(addr_start, addr_end, "address", addr_text, block_idx))

    if isinstance(block.location, CellLocation) and not spans:
        if _PIN_CODE_RE.search(text) and _STATE_RE.search(text) and 'india' in text.lower():
            india_end_m = re.search(r'India\s*[;,.\n]?', text, re.IGNORECASE)
            if india_end_m and len(text[:india_end_m.end()].strip()) > 20:
                spans.append(PIISpan(0, india_end_m.end(), "address", text[:india_end_m.end()].strip().rstrip(';,.'), block_idx))

    return spans


# --- spaCy NER Model Loader & Filters ---
_nlp: Optional[Language] = None

_EXTRA_DENYLIST_LOWER: Set[str] = {
    'mr', 'mrs', 'ms', 'dr', 'shri', 'smt', 'email', 'e-mail',
    'telephone', 'tel', 'fax', 'website', 'address',
    'bid', 'bidder', 'bidders', 'offer', 'pre-offer', 'post-offer',
    'floor price', 'cap price', 'offer price', 'anchor investor',
    'mutual funds', 'mutual fund', 'upi bidders', 'upi bidder',
    'selling shareholder', 'promoter selling shareholder',
    'share transfer agents', 'registrar', 'registrars',
    'alpha', 'beta', 'gamma', 'phase',
    'corrigenda thereto', 'pursuant', 'excludes',
    'parents branch', 'reference rate',
    'key managerial personnel', 'compliance officer',
    'registered broker', 'a registered broker',
    'depository participant', 'designated intermediary',
}

_NAME_POISON_WORDS: Set[str] = {
    'private', 'limited', 'pvt', 'ltd', 'llp', 'llc', 'inc',
    'corporation', 'corp', 'company', 'co',
    'bank', 'trust', 'foundation', 'society', 'association',
    'facility', 'park', 'industrial', 'international',
    'securities', 'wealth', 'management', 'finance',
    'investor', 'investors', 'bidder', 'bidders',
    'offer', 'price', 'share', 'shares', 'equity',
    'fund', 'funds', 'mutual', 'insurance',
    'office', 'branch', 'floor', 'building', 'tower',
    'road', 'marg', 'nagar', 'complex', 'east', 'west',
    'north', 'south', 'district', 'taluka',
    'transfer', 'agent', 'agents', 'website', 'email',
    'regulation', 'regulations', 'act', 'section',
    'iso', 'certificate', 'certified',
    'shareholder', 'shareholders', 'promoter', 'promoters',
    'personnel', 'managerial', 'amount', 'slip', 'schedule',
    'defaulter', 'account', 'kilometers', 'kilometer', 'conditioning',
    'amperes', 'volt-amperes', 'voltaic', 'margin', 'cagr',
    'measures', 'operational', 'hospital', 'showroom', 'chambers',
    'bhavan', 'pune', 'mumbai', 'bhopal', 'listing', 'circulated',
    'newspaper', 'daily', 'jyoti', 'urja', 'suraksha', 'electricals',
    'bandra', 'vikhroli', 'shivajinagar', 'reclamation', 'churchgate',
    'peth', 'colony', 'huf',
}


def get_nlp() -> Optional[Language]:
    """Lazy-load spaCy model."""
    global _nlp
    if _nlp is None and spacy is not None:
        try:
            _nlp = spacy.load(SPACY_MODEL)
            log.info(f"Loaded spaCy model: {SPACY_MODEL}")
        except OSError:
            log.warning(f"spaCy model '{SPACY_MODEL}' not found.")
            return None
    return _nlp


@register_detector("person_name")
def detect_names(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect person names using spaCy NER with aggressive false-positive filtering."""
    nlp = get_nlp()
    if nlp is None:
        return []

    spans: List[PIISpan] = []
    doc = nlp(block.text)
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue

        name = ent.text.strip()
        if (
            name.upper() in PERSON_DENYLIST
            or len(name) < 4
            or re.sub(r'[\s\-\.]', '', name).isdigit()
            or name.lower().strip() in _EXTRA_DENYLIST_LOWER
        ):
            continue

        words = name.split()
        if len(words) < 2:
            continue

        name_lower_words = {w.lower().rstrip('.,;:/') for w in words}
        if name_lower_words & _NAME_POISON_WORDS:
            continue

        cap_words = [w for w in words if w[0].isupper() and len(w) > 1]
        if len(cap_words) < 2:
            continue

        if name == name.upper() and len(name) > 5:
            continue

        if '@' in name or re.search(r'\d', name) or re.search(r'[^a-zA-Z\s.\-\']', name) or name[0].islower() or '\t' in name:
            continue

        spans.append(PIISpan(ent.start_char, ent.end_char, "person_name", name, block_idx))

    return spans


@register_detector("company_name")
def detect_orgs(block: TextBlock, block_idx: int) -> List[PIISpan]:
    """Detect company/organization names using spaCy NER."""
    nlp = get_nlp()
    if nlp is None:
        return []

    spans: List[PIISpan] = []
    doc = nlp(block.text)
    for ent in doc.ents:
        if ent.label_ == "ORG":
            org = ent.text.strip()
            if len(org) >= 3 and org.upper() not in PERSON_DENYLIST:
                spans.append(PIISpan(ent.start_char, ent.end_char, "company_name", org, block_idx))
    return spans
