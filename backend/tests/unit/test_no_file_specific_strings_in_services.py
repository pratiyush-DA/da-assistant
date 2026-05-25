"""Guard: production services must not embed demo file/customer literals."""

import re
from pathlib import Path

SERVICES_ROOT = Path(__file__).resolve().parents[2] / "services"

BANNED = re.compile(r"\b(FOIA|Agency|ReportTitle)\b", re.I)

ALLOWED_PATH_FRAGMENTS = (
    "sheet_profiles.py",
)


def test_services_have_no_file_specific_literals():
    violations: list[str] = []
    for path in SERVICES_ROOT.rglob("*.py"):
        if any(frag in path.as_posix() for frag in ALLOWED_PATH_FRAGMENTS):
            continue
        text = path.read_text(encoding="utf-8")
        for match in BANNED.finditer(text):
            line_no = text[: match.start()].count("\n") + 1
            violations.append(f"{path.relative_to(SERVICES_ROOT)}:{line_no}: {match.group()}")
    assert not violations, "Banned literals in services:\n" + "\n".join(violations)
