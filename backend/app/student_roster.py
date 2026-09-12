"""Load the supplied student roster only when it exists on the local machine.

The PDF is deliberately ignored by Git. This module keeps personal details out of
the repository while allowing the locally authorised college database to use the
provided roster. Deployments without that private source keep synthetic profiles.
"""
from pathlib import Path
import re

from pypdf import PdfReader


ROSTER_PATH = Path(__file__).resolve().parents[2] / "College Details Assets" / "Student Details.pdf"
ROSTER_PATTERN = re.compile(r"^\s*(\d+)\s+(\d+)\s+(.+?)\s+(NP01CP4A\d+)\s*$", re.MULTILINE)


def _display_name(value: str) -> str:
    return " ".join(part if "." in part else part.capitalize() for part in value.split())


def load_private_student_roster() -> list[dict[str, str]]:
    """Return non-empty only for the locally supplied Computing roster."""
    if not ROSTER_PATH.exists():
        return []
    text = "\n".join(page.extract_text() or "" for page in PdfReader(ROSTER_PATH).pages)
    rows = [
        {
            "london_met_id": london_met_id,
            "name": _display_name(name),
            "college_id": college_id,
        }
        for _, london_met_id, name, college_id in ROSTER_PATTERN.findall(text)
    ]
    return rows if len(rows) == 276 and len({row["college_id"] for row in rows}) == 276 else []
