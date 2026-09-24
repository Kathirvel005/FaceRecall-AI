from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import numpy as np

from backend.app.config import settings
from backend.app.schemas.recognition import QualityMetrics
from backend.app.ml.vector_store import SearchResult, FAISSVectorStore

class MatchDecision:
    def __init__(
        self,
        person_id: Optional[str],
        name: str,
        status: str,  # KNOWN, UNKNOWN, LOW_QUALITY, VERIFYING
        similarity: float,
        confidence: float,
        details: Dict[str, Any]
    ):
        self.person_id = person_id
        self.name = name
        self.status = status
        self.similarity = similarity
        self.confidence = confidence
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "person_id": self.person_id,
            "name": self.name,
            "status": self.status,
            "similarity": round(self.similarity, 4),
            "confidence": round(self.confidence, 4),
            "details": self.details
        }


class IdentityMatcher:
    """
    Quality-Aware Identity Matching Engine with anti-false-match safeguards,
    multi-sample aggregation, and explicit UNKNOWN classification.
    """

    def __init__(
        self,
        similarity_threshold: float = settings.SIMILARITY_THRESHOLD,
        unknown_threshold: float = settings.UNKNOWN_THRESHOLD,
        top_k: int = settings.TOP_K_CANDIDATES
    ):
        self.similarity_threshold = similarity_threshold
        self.unknown_threshold = unknown_threshold
        self.top_k = top_k

    def match(
        self,
        candidates: List[SearchResult],
        quality: QualityMetrics
    ) -> MatchDecision:
        """
        Evaluate candidate search results and quality metrics to make a robust identity decision.
        """
        # 1. Quality Filter Check
        if not quality.is_valid:
            return MatchDecision(
                person_id=None,
                name="LOW QUALITY",
                status="LOW_QUALITY",
                similarity=0.0,
                confidence=quality.quality_score,
                details={"reason": quality.reason, "quality": quality.quality_score}
            )

        # 2. No candidates in database
        if not candidates:
            return MatchDecision(
                person_id=None,
                name="UNKNOWN",
                status="UNKNOWN",
                similarity=0.0,
                confidence=0.0,
                details={"reason": "NO_REGISTERED_IDENTITIES"}
            )

        # 3. Aggregate candidates by person_id (multiple face samples per person)
        person_scores: Dict[str, List[float]] = defaultdict(list)
        person_metas: Dict[str, Dict[str, Any]] = {}

        for cand in candidates:
            pid = cand.person_id
            person_scores[pid].append(cand.similarity)
            if pid not in person_metas:
                person_metas[pid] = cand.metadata

        # Compute aggregate score per candidate identity (top-score with frequency boost)
        aggregated: List[Tuple[str, float, Dict[str, Any]]] = []
        for pid, scores in person_scores.items():
            top_score = max(scores)
            avg_score = float(np.mean(scores))
            # Blended score: 70% top score, 30% average across matching samples
            blended = 0.70 * top_score + 0.30 * avg_score
            aggregated.append((pid, blended, person_metas[pid]))

        # Sort descending by aggregated score
        aggregated.sort(key=lambda x: x[1], reverse=True)
        best_pid, best_score, best_meta = aggregated[0]
        best_name = str(best_meta.get("name", "UNKNOWN"))

        # 4. Anti-False-Match Ambiguity Check:
        # If top 2 candidates are different persons with negligible difference, flag as VERIFYING
        if len(aggregated) > 1:
            second_pid, second_score, _ = aggregated[1]
            if second_pid != best_pid and (best_score - second_score) < 0.03 and best_score >= self.similarity_threshold:
                return MatchDecision(
                    person_id=best_pid,
                    name=best_name,
                    status="VERIFYING",
                    similarity=best_score,
                    confidence=best_score * quality.quality_score,
                    details={"reason": "AMBIGUOUS_CLOSE_MATCH", "second_score": round(second_score, 4)}
                )

        # 5. Threshold Checks: KNOWN (Green) if score meets threshold, otherwise UNKNOWN (Red)
        if best_score >= self.similarity_threshold:
            return MatchDecision(
                person_id=best_pid,
                name=best_name,
                status="KNOWN",
                similarity=best_score,
                confidence=best_score * quality.quality_score,
                details={"matched_samples": len(person_scores[best_pid])}
            )
        else:
            return MatchDecision(
                person_id=None,
                name="UNKNOWN",
                status="UNKNOWN",
                similarity=best_score,
                confidence=1.0 - best_score,
                details={"reason": f"SIMILARITY_BELOW_THRESHOLD ({best_score:.3f} < {self.similarity_threshold})"}
            )


identity_matcher = IdentityMatcher()
