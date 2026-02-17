import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from collections import Counter

class DeepAnalyzer:
    def __init__(self, model):
        self.model = model

    def analyze_clusters(self, embeddings, df_findings):
        """
        Performs DBSCAN clustering to find semantic groupings of findings.
        Returns:
            - labeled_df: DataFrame with 'Cluster' column
            - clusters_summary: List of dicts describing each cluster
        """
        if len(embeddings) < 5:
            return df_findings, []

        # 1. DBSCAN for density-based clustering (good for finding outliers/anomalies)
        # eps=0.5 is a starting point for cosine distance (if normalized) or euclidean
        # Since embeddings are normalized, we can use euclidean which is equivalent to cosine rank
        clustering = DBSCAN(eps=0.6, min_samples=3, metric='euclidean').fit(embeddings)
        labels = clustering.labels_

        df_findings['Cluster'] = labels

        # 2. Summarize Clusters
        unique_labels = set(labels)
        cluster_summary = []

        for k in unique_labels:
            if k == -1:
                # Noise / Outliers -> POTENTIAL LEAKAGE (Unique, rare issues)
                label_name = "Unclassified Anomalies (Potential Rare Leakage)"
                risk_level = "High"
            else:
                # Core Clusters -> SYSTEMIC ISSUES
                cluster_data = df_findings[df_findings['Cluster'] == k]
                # Find most common words or just take the first finding as representative
                example = cluster_data.iloc[0]['Finding']
                label_name = f"Cluster {k}: {example[:50]}..."
                risk_level = "Medium"

            count = list(labels).count(k)
            
            cluster_summary.append({
                "id": int(k),
                "name": label_name,
                "count": count,
                "risk": risk_level,
                "examples": df_findings[df_findings['Cluster'] == k]['Finding'].head(3).tolist()
            })

            # Auto-tag leakage if it's a dense cluster that hasn't been mapped to a process well
            # (Logic can be enhanced if we had process mapping scores here)

        return df_findings, cluster_summary

    def detect_trends(self, df_findings):
        """
        If 'Year' or 'Date' is present, detect trends.
        Otherwise, assume all data is current.
        """
        # Placeholder for time-series analysis if dates were provided
        return []
