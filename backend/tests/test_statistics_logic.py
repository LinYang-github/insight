
import pytest
import pandas as pd
import numpy as np
from app.services.statistics_service import StatisticsService

class TestStatisticsLogic:
    """
    Verifies S-01 and S-02 from Test Plan.
    """

    def test_s01_levene_welch_routing(self):
        """
        S-01: Hypothesis Routing: Levene/Welch
        Condition: Two groups, Group A (low variance), Group B (high variance).
        Expected: Levene P < 0.05 -> Welch's T-test.
        """
        np.random.seed(42)
        # Group A: Variance ~0 (all 10s)
        group_a = [10.0] * 50
        # Group B: High Variance (0 to 100)
        group_b = np.random.uniform(0, 100, 50).tolist()
        
        df = pd.DataFrame({
            'val': group_a + group_b,
            'group': ['A']*50 + ['B']*50
        })
        
        # Run Stats
        # API: generate_table_one(df, group_by, variables)
        results = StatisticsService.generate_table_one(df, 'group', ['val'])
        res = results[0]
        
        print(f"\n[S-01] Test: {res.get('test')} - Reason: {res.get('_meta', {}).get('reason')}")
        
        # Verify
        assert res['test'] == "Welch's T-test"
        assert "方差齐性检验显著" in res['_meta']['selection_reason']

    def test_s02_fisher_exact_routing(self):
        """
        S-02: Hypothesis Routing: Fisher Exact Test
        Condition: 2x2 table with cell count < 5.
        Expected: Fisher Exact Test.
        """
        # Construct dataframe
        # Group 1: 5 Yes, 5 No
        # Group 2: 1 Yes (Low!), 9 No
        
        data = []
        # Group A: 5 Yes, 5 No
        data.extend([{'group': 'A', 'outcome': 'Yes'}] * 5)
        data.extend([{'group': 'A', 'outcome': 'No'}] * 5)
        # Group B: 1 Yes, 9 No
        data.extend([{'group': 'B', 'outcome': 'Yes'}] * 1)
        data.extend([{'group': 'B', 'outcome': 'No'}] * 9)
        
        df = pd.DataFrame(data)
        
        results = StatisticsService.generate_table_one(df, 'group', ['outcome'])
        res = results[0]
        
        print(f"\n[S-02] Test: {res.get('test')} - Reason: {res.get('_meta', {}).get('selection_reason')}")
        
        # Verify
        assert res['test'] == "Fisher Exact Test"
        assert "期望频数 < 5" in res['_meta']['selection_reason']

    def test_s01_levene_student_routing(self):
        """
        Counter-case for S-01: Equal Variance -> Student's T-test.
        """
        np.random.seed(42)
        # Equal variance
        group_a = np.random.normal(10, 2, 50)
        group_b = np.random.normal(12, 2, 50)
        
        df = pd.DataFrame({
            'val': np.concatenate([group_a, group_b]),
            'group': ['A']*50 + ['B']*50
        })
        
        results = StatisticsService.generate_table_one(df, 'group', ['val'])
        res = results[0]
        
        print(f"\n[S-01-Normal] Test: {res.get('test')} - Reason: {res.get('_meta', {}).get('reason')}")
        
        assert res['test'] == "Student's T-test"
