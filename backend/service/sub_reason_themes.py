"""Groups the free-text `sub_reason` column into chartable themes.

`sub_reason` is AI-written narrative, not a category: 440 distinct values across
716 rows, averaging 39 characters. Charting it raw is useless, so these ordered
keyword rules fold it into themes. Rules are first-match-wins, which is why the
order matters -- "Father's illness" must reach the family rule before the
generic illness rule, and "Uncle's death" must reach bereavement before either.

Keywords were derived from a frequency scan of the real column, not guessed.
Anything unmatched lands in OTHER_THEME so totals always reconcile.
"""

from sqlalchemy import case, or_

UNSPECIFIED_THEME = "Unspecified"
OTHER_THEME = "Other / Unclassified"

# (theme label, keyword fragments matched case-insensitively) -- ordered.
SUB_REASON_THEMES: list[tuple[str, tuple[str, ...]]] = [
    (
        "Bereavement / Death",
        ("death", "bereavement", "funeral", "passed away", "expired", "demise"),
    ),
    (
        "Family Health / Emergency",
        (
            "wife", "father", "mother", "sister", "brother", "child", "son's",
            "daughter", "husband", "parent", "in-law", "uncle", "aunt",
        ),
    ),
    (
        "Surgery / Hospitalization",
        (
            "surgery", "operation", "hospitaliz", "hospital", "treatment",
            "delivery", "admitted", "scan", "biopsy",
        ),
    ),
    (
        "Accident / Injury",
        ("accident", "injur", "fracture", "wound", "burn", "ligament", "sprain"),
    ),
    (
        "Marriage / Family Function",
        (
            "marriage", "wedding", "function", "festival", "temple", "ceremony",
            "pooja", "puja", "engagement",
        ),
    ),
    (
        "Native / Hometown Travel",
        ("native", "hometown", "home town", "village", "travel", "out of station"),
    ),
    (
        "Illness / Fever",
        (
            "illness", "unwell", "fever", "sick", "health", "medical", "pain",
            "allergy", "loose motion", "stomach", "headache", "cold", "cough",
            "vomit", "infection", "bp ", "sugar", "not feeling",
        ),
    ),
    (
        "Resignation / Attrition",
        ("resign", "quit", "attrition", "not interested", "left the company",
         "removed", "terminat"),
    ),
    ("Exam / Education", ("exam", "college", "school", "study", "studies")),
    (
        "Salary / Payroll Issue",
        ("salary", "wage", "payment", "overtime", "bonus", "pan card", "kyc"),
    ),
    (
        "Attendance / Punch Discrepancy",
        ("punch", "attendance", "discrepancy", "mismatch", "record shows",
         "system shows", "records indicate"),
    ),
    (
        "Shift / Roster Confusion",
        ("shift", "night duty", "roster", "duty change"),
    ),
    (
        "Leave Formality / Documentation",
        ("leave letter", "written letter", "leave form", "applied for leave",
         "no-pay", "permission", "leave of absence", "submitted"),
    ),
    (
        "Transport / Weather Issue",
        ("bike", "bus ", "train", "vehicle", "rain", "flood", "breakdown",
         "puncture"),
    ),
    (
        "Personal / Domestic Issue",
        ("personal", "home problem", "problems at home", "house", "domestic",
         "dispute", "family problem", "family issue"),
    ),
    (
        "Unclear / No Intimation",
        (
            "unclear", "unspecified", "not specified", "incomplete", "no reason",
            "communication", "unintelligible", "fragmented", "did not state",
            "could not", "no clear", "not stated", "not provided", "confus",
        ),
    ),
]


def theme_expression(column):
    """A SQL CASE folding `column` into a theme label, mirroring the ordered
    rules above (SQL CASE is first-match-wins, same as the rule list)."""
    whens: list[tuple] = [(column.is_(None), UNSPECIFIED_THEME)]
    for label, keywords in SUB_REASON_THEMES:
        whens.append(
            (or_(*(column.ilike(f"%{kw}%") for kw in keywords)), label)
        )
    return case(*whens, else_=OTHER_THEME)
