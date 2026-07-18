"""Shared backend-independent memory-retrieval query helpers."""

from __future__ import annotations

import re

def _search_patterns(query: str) -> list[str]:
    """LIKE/ILIKE patterns for the keyword-fallback search paths.

    The full normalized phrase always leads (exact matches rank first);
    per-term fallback patterns are added for every token that is not an
    ``FTS_QUERY_STOPWORDS`` member, so the LIKE paths drop the same
    question words the FTS paths drop instead of matching every row that
    contains e.g. "about" or "your".
    """
    normalized = " ".join(str(query).split()).strip()
    if len(normalized) >= 2 and (
        (normalized[0] == normalized[-1] and normalized[0] in {"'", '"'})
        or (normalized[0], normalized[-1]) in {("\u201c", "\u201d"), ("\u2018", "\u2019")}
    ):
        normalized = normalized[1:-1].strip()

    patterns: list[str] = []
    if normalized:
        patterns.append(f"%{normalized}%")
    seen = {pattern.casefold() for pattern in patterns}
    for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", normalized):
        folded = term.casefold()
        if folded in FTS_QUERY_STOPWORDS:
            continue
        pattern = f"%{folded}%"
        if pattern.casefold() not in seen:
            patterns.append(pattern)
            seen.add(pattern.casefold())
    return patterns or ["%%"]


# The Snowball English stopword set mirrors PostgreSQL's ``english``
# text-search configuration. SQLite FTS5 has no stopword layer, so every
# strict, fallback, and LIKE path shares this single definition to avoid
# backend-dependent recall and question-word false positives.
FTS_QUERY_STOPWORDS = frozenset(
    """
    i me my myself we our ours ourselves you your yours yourself yourselves
    he him his himself she her hers herself it its itself they them their
    theirs themselves what which who whom this that these those am is are
    was were be been being have has had having do does did doing a an the
    and but if or because as until while of at by for with about against
    between into through during before after above below to from up down in
    out on off over under again further then once here there when where why
    how all any both each few more most other some such no nor not only own
    same so than too very s t can will just don should now
    """.split()
)


def fts_fallback_tokens(query: str) -> list[str]:
    """Sanitized non-stopword tokens for the OR-fallback FTS pass.

    ``\\w+`` extraction strips every tsquery/FTS5 metacharacter (quotes,
    ``& | ! ( ) : * -`` and friends), so no user input can inject query
    syntax on either backend.
    """
    return [token for token in re.findall(r"\w+", str(query)) if token.casefold() not in FTS_QUERY_STOPWORDS]


for _retrieval_helper in (_search_patterns, fts_fallback_tokens):
    _retrieval_helper.__module__ = "alicebot_api.vnext_store"
    _retrieval_helper.__qualname__ = _retrieval_helper.__name__
del _retrieval_helper
