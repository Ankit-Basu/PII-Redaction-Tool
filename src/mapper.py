# -*- coding: utf-8 -*-
"""Consistent fake value generation via Faker."""

from __future__ import annotations

import re
from typing import Dict, Tuple

from faker import Faker

from src.config import FAKER_SEED


class FakeMapper:
    """Generate and track consistent fake values for detected PII.

    The same real value always maps to the same fake value, keyed by
    (pii_type, normalized_value) to avoid collisions across types.
    """

    def __init__(self, seed: int = FAKER_SEED) -> None:
        self.faker = Faker(['en_IN', 'en_US'])
        Faker.seed(seed)
        self._map: Dict[Tuple[str, str], str] = {}

    def _normalize(self, pii_type: str, value: str) -> str:
        """Normalize value for consistent lookup."""
        if pii_type in ("email", "phone", "ip_address"):
            return value.lower().strip()
        if pii_type == "person_name":
            return value.strip()
        if pii_type == "din":
            return re.sub(r'\D', '', value)
        return value.strip()

    def get_fake(self, pii_type: str, real_value: str) -> str:
        """Return fake value for given real value."""
        key = (pii_type, self._normalize(pii_type, real_value))
        if key in self._map:
            return self._map[key]

        fake_value = self._generate(pii_type, real_value)
        self._map[key] = fake_value
        return fake_value

    def _generate(self, pii_type: str, real_value: str) -> str:
        """Generate fake value matching type and format."""
        if pii_type == "email":
            return f"{self.faker.user_name()}@example.com"
        elif pii_type == "phone":
            return self._fake_phone(real_value)
        elif pii_type == "person_name":
            return self._fake_name(real_value)
        elif pii_type == "company_name":
            return self.faker.company()
        elif pii_type == "address":
            return self._fake_address()
        elif pii_type == "ssn":
            return self.faker.ssn()
        elif pii_type == "credit_card":
            return self.faker.credit_card_number()
        elif pii_type == "dob":
            return self._fake_dob(real_value)
        elif pii_type == "ip_address":
            return self.faker.ipv4()
        elif pii_type == "din":
            return ''.join([str(self.faker.random_digit()) for _ in range(8)])
        else:
            return "[REDACTED]"

    def _fake_phone(self, real: str) -> str:
        """Generate fake phone preserving format."""
        if real.strip().startswith('+'):
            digits = ''.join([str(self.faker.random_digit()) for _ in range(10)])
            return f"+91 {digits[:2]} {digits[2:6]} {digits[6:]}"
        elif real.strip().startswith('0'):
            digits = ''.join([str(self.faker.random_digit()) for _ in range(8)])
            return f"0{self.faker.random_int(20, 99)}-{digits}"
        else:
            digits = ''.join([str(self.faker.random_digit()) for _ in range(10)])
            return digits

    def _fake_name(self, real: str) -> str:
        """Generate fake person name."""
        parts = real.split()
        if len(parts) >= 3:
            return f"{self.faker.first_name()} {self.faker.first_name()} {self.faker.last_name()}"
        elif len(parts) == 2:
            return f"{self.faker.first_name()} {self.faker.last_name()}"
        else:
            return self.faker.first_name()

    def _fake_address(self) -> str:
        """Generate fake Indian address."""
        street = f"{self.faker.random_int(1, 500)}, {self.faker.street_name()}"
        area = self.faker.city_suffix()
        city = self.faker.city()
        pin = f"{self.faker.random_int(100, 999)} {self.faker.random_int(100, 999)}"
        state = self.faker.state() if hasattr(self.faker, 'state') else "Maharashtra"
        return f"{street}, {area}, {city} \u2013 {pin}, {state}, India"

    def _fake_dob(self, real: str) -> str:
        """Generate fake DOB."""
        fake_date = self.faker.date_of_birth(minimum_age=25, maximum_age=70)
        if '/' in real:
            return fake_date.strftime('%d/%m/%Y')
        elif '-' in real and len(real.split('-')[0]) <= 2:
            return fake_date.strftime('%d-%m-%Y')
        else:
            return fake_date.strftime('%B %d, %Y')

    def get_mapping(self) -> Dict[str, Dict[str, str]]:
        """Return mapping dictionary."""
        result: Dict[str, Dict[str, str]] = {}
        for (pii_type, normalized), fake in self._map.items():
            result.setdefault(pii_type, {})[normalized] = fake
        return result
