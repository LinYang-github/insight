import pytest
import pandas as pd
import numpy as np
from app.services.advanced_modeling_service import AdvancedModelingService

class TestCoxComparison:
    
    @pytest.fixture
    def cox_df(self):
        np.random.seed(42)
        n = 200
        df = pd.DataFrame({
            'duration': np.random.exponential(10, n),
            'event': np.random.choice([0, 1], n, p=[0.3, 0.7]), # 70% events
            'age': np.random.normal(60, 10, n), # Baseline predictor
            'biomarker': np.random.normal(5, 2, n) # New predictor
        })
        # Add some signal
        # Higher biomarker -> Higher risk (shorter duration)
        # Hazard ~ exp(0.1*age + 0.3*biomarker)
        # We simulate this loosely by correlating duration
        df['duration'] = 100 / (1 + np.exp(0.05*df['age'] + 0.2*df['biomarker'])) + np.random.normal(0, 2, n)
        df['duration'] = df['duration'].clip(lower=0.1)
        return df

    def test_cox_comparison_metrics(self, cox_df):
        """
        Verify that Cox comparison returns multiple time points and valid NRI/IDI/Delong metrics.
        """
        model_configs = [
            {'name': 'Basic', 'features': ['age']},
            {'name': 'Full', 'features': ['age', 'biomarker']}
        ]
        
        # Run Comparison
        res_list = AdvancedModelingService.compare_models(
            cox_df,
            target='duration',
            event_col='event',
            model_configs=model_configs,
            model_type='cox'
        )
        
        assert len(res_list) == 2, "Should return results for 2 models"
        
        # Check Model 1 (Basic)
        m1 = res_list[0]
        metrics1 = m1['metrics']
        assert 'time_dependent' in metrics1
        assert 'available_time_points' in metrics1
        time_points = metrics1['available_time_points']
        
        print(f"\nTime Points: {time_points}")
        assert len(time_points) == 3, "Should have 3 evaluation time points (quartiles)"
        
        # Check key structure for time_dependent
        t_mid = time_points[1] # Use median point
        td1 = metrics1['time_dependent'][t_mid]
        assert 'auc' in td1
        assert 'roc_data' in td1
        assert 'p_eval' in td1 # Should be present as list (internal use)
        assert isinstance(td1['p_eval'], list), "p_eval should be converted to list for JSON serialization"
        
        # Check Model 2 (Full) - This is where Comparison Metrics live
        m2 = res_list[1]
        metrics2 = m2['metrics']
        td2 = metrics2['time_dependent'][t_mid]
        
        # 1. Check if NRI/IDI exist
        print(f"\nModel 2 Metrics at t={t_mid}: {td2.keys()}")
        assert 'nri' in td2, "NRI should be calculated for Model 2"
        assert 'idi' in td2, "IDI should be calculated for Model 2"
        assert 'p_delong' in td2, "Delong P-value should be calculated for Model 2"
        
        # 2. Check values are valid types (not None, not NaN ideally, but float)
        assert isinstance(td2['nri'], (float, int))
        assert isinstance(td2['idi'], (float, int))
        
        # 3. Check JSON serializability (Mock test by running json.dumps)
        import json
        try:
            json_str = json.dumps(res_list)
            print("\nJSON Serialization: Success")
        except TypeError as e:
            pytest.fail(f"JSON Serialization failed: {e}")

if __name__ == "__main__":
    t = TestCoxComparison()
    # Manual run setup if running direct python script
    df = t.cox_df()
    t.test_cox_comparison_metrics(df)
    print("Test passed!")
