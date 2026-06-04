"""
utilities/col_resolver.py - NLP functions for resolving messy real column names to canonical names using token overlap.
Responsibilities:
- Resolve messy real column names to canonical names using token overlap.
- Called once per file, before the row loop, so validators never hardcode column strings.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("data_pipeline.col_resolver")

# Lowercase, strip parenthetical suffixes, split on non-alpha separators.
#     'Hourly Rate (SGD)' - {'hourly', 'rate'}
#     'start_date'        - {'start', 'date'}
#     'Invoice Date'      - {'invoice', 'date'}
#     'Status'            - {'status'}
def _tokenise(name: str) -> set[str]:
    name = re.sub(r"\(.*?\)", "", name)   # drop anything in parens: (SGD), (yyyy-mm-dd)
    name = name.lower()
    tokens = set(re.split(r"[\s_\-/]+", name))
    tokens.discard("")
    return tokens


# Jaccard similarity with a canonical-coverage guard.

# Problem without the guard: a bare 'Rate' would match 'hourly rate' at 0.5
# (1 shared / 2 union) — a false positive since 'Rate' is ambiguous on its own.

# Fix: if the actual column has FEWER tokens than the canonical name, require
# that the intersection covers at least 75% of the canonical tokens.
# 'Rate' vs 'hourly rate' - 1/2 = 0.50 < 0.75 - score forced to 0
# 'Invoice ID' vs 'invoice id' - 2/2 = 1.00 ≥ 0.75 - normal Jaccard
# 'Status' vs 'status' - equal length, guard skipped - 1.0
def _match_score(actual_tokens: set[str], canonical_tokens: set[str]) -> float:
    if not actual_tokens or not canonical_tokens:
        return 0.0

    intersection = actual_tokens & canonical_tokens

    if len(actual_tokens) < len(canonical_tokens):
        canon_coverage = len(intersection) / len(canonical_tokens)
        if canon_coverage < 0.75:
            return 0.0

    union = actual_tokens | canonical_tokens
    return len(intersection) / len(union)

# Map each canonical column name to the best-matching actual column name.
# Returns a dict {canonical_name: actual_col_name}.
# Canonical columns with no match above `threshold` are omitted —
# the validator treats them as absent (triggers MISSING_REQUIRED_FIELD for
# required fields; silently ignored for optional ones).

#     Longer canonical names are resolved first so that 'payment date' claims its
#     column before 'date' can steal it
def resolve_columns(
    actual_columns: list[str],
    canonical_columns: list[str],
    threshold: float = 0.4,
) -> dict[str, str]:
    
    canonical_tokens = {c: _tokenise(c) for c in canonical_columns}
    actual_tokens    = {a: _tokenise(a) for a in actual_columns}

    mapping: dict[str, str] = {}
    used_actual: set[str] = set()

    for canon in sorted(canonical_columns, key=lambda c: len(_tokenise(c)), reverse=True):
        best_score = 0.0
        best_actual: Optional[str] = None

        for actual, atoks in actual_tokens.items():
            if actual in used_actual:
                continue
            score = _match_score(atoks, canonical_tokens[canon])
            if score > best_score:
                best_score = score
                best_actual = actual

        if best_actual is not None and best_score >= threshold:
            mapping[canon] = best_actual
            used_actual.add(best_actual)
            logger.debug(
                "Column resolved",
                extra={
                    "canonical": canon,
                    "actual": best_actual,
                    "score": round(best_score, 2),
                },
            )
        else:
            logger.warning(
                "No column match found",
                extra={"canonical": canon, "best_score": round(best_score, 2)},
            )

    return mapping

# Safe column-map getter.
# rget(raw, col_map, "hourly rate") → raw["Hourly Rate (SGD)"]
# Returns None if the canonical key was not resolved (unmatched column).
def rget(raw: dict, col_map: dict[str, str], canonical_key: str):
    actual = col_map.get(canonical_key)
    if actual is None:
        return None
    return raw.get(actual)