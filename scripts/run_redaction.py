# -*- coding: utf-8 -*-
"""CLI Entry Point to run PII Redaction Tool."""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.config import ENABLED_PII_TYPES, REDACT_TOLL_FREE
from src.redactor import Redactor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("pii_redactor")


def main() -> None:
    """Run CLI Redaction process."""
    parser = argparse.ArgumentParser(description="PII Redaction Tool for DOCX")
    parser.add_argument(
        "--input", "-i",
        default=str(root_dir / "data" / "Red_Herring_Prospectus.docx"),
        help="Path to input .docx file",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(root_dir / "output" / "redacted_output.docx"),
        help="Path to output .docx file",
    )
    parser.add_argument(
        "--log", "-l",
        default=str(root_dir / "output" / "detection_log.json"),
        help="Path to output detection log JSON file",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("PII Redaction Tool — Execution")
    log.info("=" * 60)
    log.info(f"Enabled PII types: {[k for k, v in ENABLED_PII_TYPES.items() if v]}")
    log.info(f"Redact toll-free: {REDACT_TOLL_FREE}")

    redactor = Redactor(
        input_path=args.input,
        output_path=args.output,
        log_path=args.log,
    )
    redactor.run()

    log.info("=" * 60)
    log.info("Redaction successfully completed!")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
