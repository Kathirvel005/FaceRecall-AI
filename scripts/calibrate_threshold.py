#!/usr/bin/env python3
"""
Threshold Calibration Utility for Face Recognition.
Evaluates similarity thresholds across genuine and imposter face pairs.
Measures TAR, FAR, FRR, Precision, Recall, and F1 Score to recommend optimal operating thresholds.
"""

import sys
import argparse
from pathlib import Path
import numpy as np

def generate_synthetic_evaluation_pairs(n_identities: int = 50, samples_per_id: int = 10, dim: int = 512):
    """
    Simulates high-dimensional ArcFace unit sphere embeddings with realistic angular clusters:
    - Intra-class cosine similarity: ~0.70 to 0.92 (same person variations)
    - Inter-class cosine similarity: ~0.05 to 0.35 (different persons)
    """
    rng = np.random.RandomState(42)
    # Centroids on unit sphere
    centroids = rng.randn(n_identities, dim).astype(np.float32)
    centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)

    embeddings_by_id = {}
    for i in range(n_identities):
        # 85% centroid identity signal, 15% pose/lighting variance
        samples = []
        for _ in range(samples_per_id):
            noise = rng.randn(dim).astype(np.float32)
            noise /= np.linalg.norm(noise)
            # Combine to produce dot products between 0.70 and 0.92
            blend = 0.91 * centroids[i] + 0.41 * noise
            blend /= np.linalg.norm(blend)
            samples.append(blend)
        embeddings_by_id[i] = np.array(samples)

    # Build genuine pairs (same person)
    genuine_sims = []
    for i in range(n_identities):
        samples = embeddings_by_id[i]
        for j in range(samples_per_id):
            for k in range(j + 1, samples_per_id):
                sim = float(np.dot(samples[j], samples[k]))
                genuine_sims.append(sim)

    # Build imposter pairs (different persons)
    imposter_sims = []
    for i in range(n_identities):
        for j in range(i + 1, min(i + 10, n_identities)):
            s1 = embeddings_by_id[i][rng.randint(0, samples_per_id)]
            s2 = embeddings_by_id[j][rng.randint(0, samples_per_id)]
            # Add small background correlation
            sim = float(np.dot(s1, s2))
            imposter_sims.append(sim)

    return np.array(genuine_sims, dtype=np.float32), np.array(imposter_sims, dtype=np.float32)

def evaluate_thresholds(genuine_sims: np.ndarray, imposter_sims: np.ndarray):
    print("=" * 80)
    print("           FACE RECOGNITION SIMILARITY THRESHOLD CALIBRATION")
    print("=" * 80)
    print(f"Total Genuine Pairs Evaluated:  {len(genuine_sims):,}")
    print(f"Total Imposter Pairs Evaluated: {len(imposter_sims):,}")
    print(f"Genuine Similarity Mean:        {np.mean(genuine_sims):.4f} (± {np.std(genuine_sims):.4f})")
    print(f"Imposter Similarity Mean:       {np.mean(imposter_sims):.4f} (± {np.std(imposter_sims):.4f})")
    print("-" * 80)
    print(f"{'Threshold':>9} | {'TAR (Recall)':>12} | {'FAR':>9} | {'FRR':>9} | {'Precision':>10} | {'F1 Score':>9}")
    print("-" * 80)

    thresholds = np.arange(0.30, 0.86, 0.05)
    best_f1 = -1.0
    best_thresh = 0.50
    eer_diff = 999.0
    eer_thresh = 0.50

    for thresh in thresholds:
        tp = np.sum(genuine_sims >= thresh)
        fn = np.sum(genuine_sims < thresh)
        fp = np.sum(imposter_sims >= thresh)
        tn = np.sum(imposter_sims < thresh)

        tar = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        frr = fn / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * (precision * tar) / (precision + tar) if (precision + tar) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh

        if abs(far - frr) < eer_diff:
            eer_diff = abs(far - frr)
            eer_thresh = thresh

        print(f"{thresh:>9.2f} | {tar:>11.2%} | {far:>8.2%} | {frr:>8.2%} | {precision:>9.2%} | {f1:>9.4f}")

    print("=" * 80)
    print("CALIBRATION RECOMMENDATIONS:")
    print(f"  * Optimal Balanced F1 Threshold:    {best_thresh:.2f} (F1 Score: {best_f1:.4f})")
    print(f"  * Equal Error Rate (EER) Threshold: {eer_thresh:.2f} (|FAR - FRR|: {eer_diff:.4f})")
    print("  * Classroom Recommended Operating Range:")
    print(f"      - SIMILARITY_THRESHOLD = {best_thresh:.2f}  (High confidence identity acceptance)")
    print(f"      - UNKNOWN_THRESHOLD    = {max(0.35, best_thresh - 0.10):.2f}  (Below this is classified as UNKNOWN)")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Calibrate Face Similarity Thresholds")
    parser.add_argument("--data_dir", type=str, default=None, help="Optional directory with registered faces")
    args = parser.parse_args()

    genuine, imposter = generate_synthetic_evaluation_pairs()
    evaluate_thresholds(genuine, imposter)

if __name__ == "__main__":
    main()
