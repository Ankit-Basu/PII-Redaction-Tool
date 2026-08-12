# -*- coding: utf-8 -*-
"""Configuration and constants for PII Redaction Tool."""

from typing import Dict, Set

#: Toggle each PII type on/off.
ENABLED_PII_TYPES: Dict[str, bool] = {
    "email": True,
    "phone": True,
    "person_name": True,
    "company_name": False,   # Disabled by default to preserve legal readability
    "address": True,
    "ssn": True,
    "credit_card": True,
    "dob": True,
    "ip_address": True,
    "din": True,
}

#: Whether to redact public toll-free numbers (1800-xxx-xxxx).
REDACT_TOLL_FREE: bool = False

#: Faker seed for reproducible fake values.
FAKER_SEED: int = 42

#: spaCy model name.
SPACY_MODEL: str = "en_core_web_sm"

#: Known non-person entities that spaCy may mis-tag as PERSON.
PERSON_DENYLIST: Set[str] = {
    "SEBI", "ROC", "BSE", "NSE", "RBI", "NSDL", "CDSL", "ASBA", "ICDR",
    "MCA", "CARE", "IPO", "QIB", "NII", "RII", "UPI", "BRLM", "BRLMS",
    "RHP", "DRHP", "PAN", "NRE", "NRO", "FEMA", "SCRA", "SCRR", "AIF",
    "SCSBS", "RTAS", "CDPS", "PCNTDA", "IRDAI", "EPS", "NAV", "SM", "SMS",
    "KMP", "KMPS", "CEO", "CFO", "CS", "CIN", "DIN", "AOA", "MOA",
    "AGM", "EGM", "NCLT", "NCLAT", "SAT", "ITAT", "PNGRB",
    "INDIA", "OFFER", "EQUITY", "COMPANY", "BOARD", "PROMOTER",
    "PROMOTERS", "DIRECTORS", "DIRECTOR", "SHAREHOLDERS", "FRESH ISSUE",
    "FISCAL", "NET WORTH", "NET PROCEEDS", "OFFER PRICE",
}

#: Indian state names for address detection.
INDIAN_STATES: Set[str] = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
    "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
    "Uttarakhand", "West Bengal", "Delhi", "New Delhi", "Chandigarh",
    "Puducherry", "Jammu and Kashmir", "Ladakh",
}
