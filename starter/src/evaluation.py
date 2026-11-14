"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def is_chunk_hit(hit: dict[str, Any], gold_page: int, evidence_quote: str) -> bool:
    """Check if a retrieved chunk matches the gold page and contains the gold evidence."""
    if int(hit.get("page", -1)) != int(gold_page):
        return False

    chunk_text = " ".join(hit.get("text", "").split()).lower()
    clean_ev = " ".join(evidence_quote.split()).lower()

    # Exact evidence match or strong prefix/substring match
    if clean_ev in chunk_text:
        return True

    # If long quote, check key 60-character anchor substring
    if len(clean_ev) > 60 and clean_ev[:60] in chunk_text:
        return True

    return False


def evaluate_query(
    question: dict[str, Any],
    hits: list[dict[str, Any]],
    strategy: str = "A",
) -> dict[str, Any]:
    """Check source/page and enough gold evidence; keep hit@1 and hit@3 trace."""
    gold_page = question["gold_page"]
    gold_source_id = question.get("gold_source_id", "")
    evidence_quote = question.get("evidence_quote", "")
    filter_criteria = question.get("filter")

    evaluated_hits: list[dict[str, Any]] = []
    has_hit_1 = False
    has_hit_3 = False
    filter_compliant = True

    for rank, h in enumerate(hits[:3], start=1):
        hit_match = is_chunk_hit(h, gold_page, evidence_quote)
        if rank == 1 and hit_match:
            has_hit_1 = True
        if hit_match:
            has_hit_3 = True

        # Check filter compliance if filter was specified
        if filter_criteria:
            for k, expected_v in filter_criteria.items():
                actual_v = h.get(k) or (h.get("metadata", {}).get(k))
                if str(actual_v) != str(expected_v):
                    filter_compliant = False

        evaluated_hits.append({
            "rank": rank,
            "chunk_id": h.get("chunk_id"),
            "page": h.get("page"),
            "score": h.get("score"),
            "distance": h.get("distance"),
            "is_hit": hit_match,
            "text": h.get("text", ""),
            "section": h.get("section") or h.get("metadata", {}).get("section"),
        })

    return {
        "question_id": question["id"],
        "strategy": strategy,
        "split": question.get("split", "dev"),
        "type": question.get("type", "direct"),
        "question": question["question"],
        "expected_answer": question.get("expected_answer", ""),
        "gold_page": gold_page,
        "gold_source_id": gold_source_id,
        "evidence_quote": evidence_quote,
        "filter": filter_criteria,
        "filter_compliant": filter_compliant if filter_criteria else None,
        "hit_at_1": has_hit_1,
        "hit_at_3": has_hit_3,
        "hits": evaluated_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    if not traces:
        return {}

    summary: dict[str, Any] = {}
    splits = ["all", "dev", "test"]

    for sp in splits:
        if sp == "all":
            subset = traces
        else:
            subset = [t for t in traces if t.get("split") == sp]

        count = len(subset)
        if count == 0:
            continue

        hit1_count = sum(1 for t in subset if t.get("hit_at_1"))
        hit3_count = sum(1 for t in subset if t.get("hit_at_3"))

        # Filtered questions compliance
        filter_subset = [t for t in subset if t.get("filter") is not None]
        filter_total = len(filter_subset)
        filter_ok = sum(1 for t in filter_subset if t.get("filter_compliant"))

        summary[sp] = {
            "total_questions": count,
            "hit_at_1": {
                "count": hit1_count,
                "ratio": f"{hit1_count}/{count}",
                "rate": round(hit1_count / count, 4),
            },
            "evidence_hit_at_3": {
                "count": hit3_count,
                "ratio": f"{hit3_count}/{count}",
                "rate": round(hit3_count / count, 4),
            },
            "filter_compliance": {
                "count": filter_ok,
                "total": filter_total,
                "ratio": f"{filter_ok}/{filter_total}" if filter_total > 0 else "N/A",
                "rate": round(filter_ok / filter_total, 4) if filter_total > 0 else 1.0,
            },
        }

    return summary
