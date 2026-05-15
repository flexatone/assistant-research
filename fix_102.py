# Fix for Issue #102 - Research Assistant Enhancement
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class ResearchResult:
    title: str
    abstract: str
    relevance_score: float = 0.0
    source: str = ""

def rank_by_relevance(results: List[ResearchResult], query: str) -> List[ResearchResult]:
    query_terms = set(query.lower().split())
    for r in results:
        title_terms = set(r.title.lower().split())
        abstract_terms = set(r.abstract.lower().split())
        overlap = len(query_terms & (title_terms | abstract_terms))
        r.relevance_score = overlap / max(len(query_terms), 1)
    return sorted(results, key=lambda x: x.relevance_score, reverse=True)

def deduplicate(results: List[ResearchResult]) -> List[ResearchResult]:
    seen = set()
    unique = []
    for r in results:
        key = r.title.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique
