# Fix #102
from typing import List
@dataclass
class R:
    title: str
    score: float = 0

def rank(items: List[R], q: str) -> List[R]:
    t = set(q.lower().split())
    for i in items: i.score = len(t & set(i.title.lower().split()))
    return sorted(items, key=lambda x: -x.score)
