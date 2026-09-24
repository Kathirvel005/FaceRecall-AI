from typing import Dict, List, Optional, Tuple, Any
from collections import deque, Counter
import numpy as np
from backend.app.config import settings
from backend.app.services.matching_service import MatchDecision

class TrackIdentityHistory:
    def __init__(self, window_size: int = settings.TEMPORAL_VOTE_WINDOW):
        self.window_size = window_size
        self.person_ids: deque = deque(maxlen=window_size)
        self.names: deque = deque(maxlen=window_size)
        self.statuses: deque = deque(maxlen=window_size)
        self.similarities: deque = deque(maxlen=window_size)
        self.qualities: deque = deque(maxlen=window_size)

    def add_observation(self, decision: MatchDecision, quality_score: float):
        self.person_ids.append(decision.person_id)
        self.names.append(decision.name)
        self.statuses.append(decision.status)
        self.similarities.append(decision.similarity)
        self.qualities.append(quality_score)

    def get_confirmed_identity(
        self,
        confirm_threshold: float = settings.TEMPORAL_CONFIRM_THRESHOLD
    ) -> Tuple[Optional[str], str, str, float, float]:
        """
        Calculates temporally smoothed identity from observation window.
        Returns:
            (confirmed_person_id, confirmed_name, confirmed_status, avg_similarity, avg_quality)
        """
        n_obs = len(self.statuses)
        if n_obs == 0:
            return None, "UNKNOWN", "UNKNOWN", 0.0, 0.0

        avg_quality = float(np.mean(self.qualities)) if self.qualities else 0.0

        # Check for dominating status
        status_counts = Counter(self.statuses)
        most_common_status, status_count = status_counts.most_common(1)[0]
        status_ratio = status_count / float(n_obs)

        # 1. If LOW_QUALITY dominates
        if most_common_status == "LOW_QUALITY" and status_ratio >= 0.5:
            return None, "LOW QUALITY", "LOW_QUALITY", 0.0, avg_quality

        # 2. Filter for KNOWN candidate observations
        known_pairs = [
            (pid, name, sim)
            for pid, name, status, sim in zip(self.person_ids, self.names, self.statuses, self.similarities)
            if status == "KNOWN" and pid is not None
        ]

        if known_pairs:
            # Group by person_id
            pid_counts = Counter([p[0] for p in known_pairs])
            best_pid, pid_count = pid_counts.most_common(1)[0]
            pid_ratio = pid_count / float(n_obs)

            if pid_ratio >= confirm_threshold:
                # Identity temporally confirmed
                matched_sims = [sim for pid, name, sim in known_pairs if pid == best_pid]
                matched_name = next(name for pid, name, sim in known_pairs if pid == best_pid)
                avg_sim = float(np.mean(matched_sims))
                return best_pid, matched_name, "KNOWN", round(avg_sim, 4), round(avg_quality, 4)
            else:
                # Some matches but below confirmation ratio -> VERIFYING
                matched_name = next(name for pid, name, sim in known_pairs if pid == best_pid)
                return best_pid, matched_name, "VERIFYING", 0.0, round(avg_quality, 4)

        # 3. If UNKNOWN dominates
        if status_counts.get("UNKNOWN", 0) / float(n_obs) >= 0.5:
            return None, "UNKNOWN", "UNKNOWN", 0.0, round(avg_quality, 4)

        return None, "VERIFYING", "VERIFYING", 0.0, round(avg_quality, 4)


class TemporalSmoothingManager:
    """
    Manages temporal identity history buffers across all active tracks.
    """

    def __init__(self, window_size: int = settings.TEMPORAL_VOTE_WINDOW):
        self.window_size = window_size
        self.histories: Dict[int, TrackIdentityHistory] = {}

    def update_track(
        self,
        track_id: int,
        decision: MatchDecision,
        quality_score: float
    ) -> Tuple[Optional[str], str, str, float, float]:
        if track_id not in self.histories:
            self.histories[track_id] = TrackIdentityHistory(self.window_size)

        history = self.histories[track_id]
        history.add_observation(decision, quality_score)
        return history.get_confirmed_identity()

    def cleanup_old_tracks(self, active_track_ids: List[int]):
        active_set = set(active_track_ids)
        to_remove = [tid for tid in self.histories.keys() if tid not in active_set]
        for tid in to_remove:
            del self.histories[tid]

temporal_smoother = TemporalSmoothingManager()
