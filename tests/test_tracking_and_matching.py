import numpy as np
import pytest
from backend.app.ml.tracker import MultiFaceTracker
from backend.app.services.matching_service import IdentityMatcher, MatchDecision
from backend.app.services.tracking_service import TemporalSmoothingManager
from backend.app.schemas.recognition import QualityMetrics
from backend.app.ml.vector_store import SearchResult

def test_tracker_association():
    tracker = MultiFaceTracker()

    # Frame 1: Two faces detected
    f1_detections = [
        ([50, 50, 150, 150], None),
        ([300, 300, 400, 400], None)
    ]
    tracks_f1 = tracker.update(f1_detections)
    assert len(tracks_f1) == 2
    id1 = tracks_f1[0].track_id
    id2 = tracks_f1[1].track_id
    assert id1 != id2

    # Frame 2: Faces move slightly (small shift)
    f2_detections = [
        ([55, 52, 155, 152], None),
        ([302, 298, 402, 398], None)
    ]
    tracks_f2 = tracker.update(f2_detections)
    assert len(tracks_f2) == 2
    new_ids = [t.track_id for t in tracks_f2]
    assert id1 in new_ids
    assert id2 in new_ids
    print(f"Tracking persistence verified. Track IDs maintained: {new_ids}")

def test_temporal_smoothing():
    smoother = TemporalSmoothingManager(window_size=5)
    tid = 101

    # Simulate fluctuating frames: Unknown -> Kathirvel -> Kathirvel -> Kathirvel
    d_unk = MatchDecision("UNKNOWN", "UNKNOWN", "UNKNOWN", 0.2, 0.2, {})
    d_k = MatchDecision("STU001", "Kathirvel", "KNOWN", 0.92, 0.92, {})

    smoother.update_track(tid, d_unk, 0.8)
    pid, name, status, sim, q = smoother.update_track(tid, d_k, 0.9)
    # With only 1 match out of 2 observations, status should be VERIFYING (not immediately confirmed)
    assert status in ("VERIFYING", "UNKNOWN")

    smoother.update_track(tid, d_k, 0.95)
    smoother.update_track(tid, d_k, 0.93)
    pid, name, status, sim, q = smoother.update_track(tid, d_k, 0.94)

    # Now 4 out of 5 observations are Kathirvel -> Confirmed KNOWN
    assert status == "KNOWN"
    assert name == "Kathirvel"
    assert pid == "STU001"
    assert sim > 0.9
    print(f"Temporal smoothing successfully confirmed: {name} ({status}) with sim={sim}")

if __name__ == "__main__":
    test_tracker_association()
    test_temporal_smoothing()
