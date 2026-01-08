import pytest
import pandas as pd
import numpy as np
import os
from app.services.eda_service import EdaService

class TestEdaService:
    @pytest.fixture
    def sample_csv(self, tmp_path):
        filepath = tmp_path / "data.csv"
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5],
            "B": [2, 4, 6, 8, 10], # Perfect correlation with A
            "C": ["cat", "dog", "cat", "bird", "dog"]
        })
        df.to_csv(filepath, index=False)
        return str(filepath)

    def test_get_basic_stats(self, sample_csv):
        stats = EdaService.get_basic_stats(sample_csv)
        
        a_stats = next(s for s in stats if s['name'] == 'A')
        assert a_stats['mean'] == 3.0
        assert a_stats['min'] == 1.0
        assert a_stats['max'] == 5.0
        
        c_stats = next(s for s in stats if s['name'] == 'C')
        assert c_stats['type'] == 'object'
        assert c_stats['unique_count'] == 3
        assert 'top_values' in c_stats

    def test_get_correlation(self, sample_csv):
        corr = EdaService.get_correlation(sample_csv)
        
        assert "A" in corr['columns']
        assert "B" in corr['columns']
        assert "C" not in corr['columns'] # Categorical ignored
        
        idx_a = corr['columns'].index('A')
        idx_b = corr['columns'].index('B')
        
        # Pearson corr(A, B) should be 1.0
        assert abs(corr['matrix'][idx_a][idx_b] - 1.0) < 1e-9

    def test_get_distribution_numerical(self, sample_csv):
        dist = EdaService.get_distribution(sample_csv, "A", bins=2)
        assert dist['type'] == 'numerical'
        assert len(dist['x']) == 2
        assert len(dist['y']) == 2
        # Sum of counts should be 5
        assert sum(dist['y']) == 5

    def test_get_distribution_categorical(self, sample_csv):
        dist = EdaService.get_distribution(sample_csv, "C")
        assert dist['type'] == 'categorical'
        # Check counts: cat=2, dog=2, bird=1
        counts = dict(zip(dist['x'], dist['y']))
        assert counts['cat'] == 2
        assert counts['bird'] == 1
