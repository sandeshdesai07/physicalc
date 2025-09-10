# backend/app/utils/parser.py
import re

# compile common regexes once
_ASSIGN_RE = re.compile(r'([a-zA-Z]\w?)\s*=\s*([-+]?\d*\.?\d+)', re.IGNORECASE)
UNIT_PATTERNS = [
    (re.compile(r'([-+]?\d*\.?\d+)\s*kg', re.IGNORECASE), 'm'),   # mass -> m
    (re.compile(r'([-+]?\d*\.?\d+)\s*m/s', re.IGNORECASE), 'v'),  # velocity -> v
    (re.compile(r'([-+]?\d*\.?\d+)\s*m\b', re.IGNORECASE), 'x'),  # position/distance -> x
    (re.compile(r'([-+]?\d*\.?\d+)\s*s\b', re.IGNORECASE), 't'),  # time -> t
]

def extract_vars(text: str) -> dict:
    """
    Extract simple numeric variables from a natural-language string.
    Returns a dict mapping variable names (strings) -> float values.
    Notes:
     - Recognizes "m=5", "v=10", "5 kg", "10 m/s", etc.
     - This is an MVP approach; upgrade with spaCy/NER for production.
    """
    if not text:
        return {}

    txt = text.replace(",", " ")
    variables = {}

    # find assignments like m=5 or v = 10
    for match in _ASSIGN_RE.finditer(txt):
        name = match.group(1)
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        variables[name] = value

    # find unit-pattern numbers (e.g., "5 kg", "10 m/s")
    for pattern, varname in UNIT_PATTERNS:
        for match in pattern.finditer(txt):
            if varname not in variables:
                try:
                    variables[varname] = float(match.group(1))
                except ValueError:
                    pass

    return variables
