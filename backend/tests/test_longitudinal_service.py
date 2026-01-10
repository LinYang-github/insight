import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
import pandas as pd
import numpy as np
from app.services.longitudinal_service import LongitudinalService

class TestLongitudinalService(unittest.TestCase):
    def setUp(self):
        # Generate synthetic longitudinal data
        # 20 patients, 5 visits each
        # Group A: Slope = -2
        # Group B: Slope = 0
        ids = []
        times = []
        outcomes = []
        groups = []
        
        np.random.seed(42)
        
        for i in range(1, 11): # Group A
            intercept = 100 + np.random.randn()
            slope = -2
            for t in range(5):
                ids.append(i)
                times.append(t)
                outcomes.append(intercept + slope*t + np.random.randn()*0.5)
                groups.append('A')
                
        for i in range(11, 21): # Group B
            intercept = 80 + np.random.randn()
            slope = 0
            for t in range(5):
                ids.append(i)
                times.append(t)
                outcomes.append(intercept + slope*t + np.random.randn()*0.5)
                groups.append('B')

        self.df = pd.DataFrame({
            'ID': ids,
            'Time': times,
            'Outcome': outcomes,
            'Group': groups,
            'Age': np.random.randint(50, 80, 100)
        })

    def test_fit_lmm_basic(self):
        """Test basic LMM fitting with fixed effects."""
        result = LongitudinalService.fit_lmm(
            self.df, 
            id_col='ID', 
            time_col='Time', 
            outcome_col='Outcome', 
            fixed_effects=['Group']
        )
        self.assertTrue(result['converged'])
        self.assertIn('summary', result)
        self.assertIn('random_effects', result)
        
        # Check coefficients logic
        # Group B is reference? "Group" column is string, statsmodels treats as categorical
        # Inspect summary to ensure Time coefficient is around -1 (avg of -2 and 0)
        # Actually since we control for Group, Time coeff should be slope of reference group?
        # Or if we check Group interaction?
        # Let's just check structure validity for now.
        summary = result['summary']
        vars = [r['variable'] for r in summary]
        self.assertIn('Intercept', vars)
        self.assertIn('Time', vars)

    def test_fit_lmm_singular(self):
        """Test LMM robustness with too few variance."""
        # Create dataset with zero variance in outcome
        df_flat = self.df.copy()
        df_flat['Outcome'] = 100
        
        try:
             # This often raises convergence warning or error
             result = LongitudinalService.fit_lmm(df_flat, 'ID', 'Time', 'Outcome')
             # Should handle or raise clean error? 
             # Service currently raises ValueError on exception.
        except ValueError as e:
             self.assertIn("failed", str(e))

    def test_clustering(self):
        """Test trajectory clustering separation."""
        # We constructed Group A (slope -2) and Group B (slope 0).
        # Clustering with K=2 should approximate this separation.
        result = LongitudinalService.cluster_trajectories(
            self.df, 'ID', 'Time', 'Outcome', n_clusters=2
        )
        self.assertIn('clusters', result)
        self.assertIn('centroids', result)
        
        clusters = result['clusters']
        # Check if IDs 1-10 are mostly in one cluster and 11-20 in another
        c_labels = [c['cluster_ordered'] for c in clusters]
        
        # We expect two distinct groups.
        # Since cluster_ordered 0 is lowest slope (most negative), Group A (-2) should be 0.
        # Group B (0) should be 1.
        
        # Map ID to Cluster
        id_to_cluster = {int(c['id']): c['cluster_ordered'] for c in clusters}
        
        group_a_clusters = [id_to_cluster[i] for i in range(1, 11)]
        group_b_clusters = [id_to_cluster[i] for i in range(11, 21)]
        
        # Allow minor misclassification due to random noise, but mode should be distinct
        mode_a = max(set(group_a_clusters), key=group_a_clusters.count)
        mode_b = max(set(group_b_clusters), key=group_b_clusters.count)
        
        self.assertNotEqual(mode_a, mode_b)
        self.assertEqual(mode_a, 0) # Expect rapid decline -> 0
        self.assertEqual(mode_b, 1) # Expect stable -> 1

    def test_variability(self):
        """Test variability calculation accuracy."""
        # Create a simple case manually
        # 1, 2, 3 -> Mean=2, SD=1, Diff=1,1 -> ARV=1
        df_simple = pd.DataFrame({
            'ID': [1, 1, 1],
            'Outcome': [1.0, 2.0, 3.0]
        })
        
        result = LongitudinalService.calculate_variability(df_simple, 'ID', 'Outcome')
        res = result[0]
        
        self.assertEqual(res['id'], '1')
        self.assertEqual(res['n_visits'], 3)
        self.assertAlmostEqual(res['mean'], 2.0)
        self.assertAlmostEqual(res['sd'], 1.0)
        self.assertAlmostEqual(res['arv'], 1.0)
        
    def test_insufficient_data(self):
        """Test clustering with insufficient data (need >=2 points per ID)."""
        df_single = pd.DataFrame({
            'ID': [1],
            'Time': [0],
            'Outcome': [100]
        })
        with self.assertRaises(ValueError):
             LongitudinalService.cluster_trajectories(df_single, 'ID', 'Time', 'Outcome')

if __name__ == '__main__':
    unittest.main()
