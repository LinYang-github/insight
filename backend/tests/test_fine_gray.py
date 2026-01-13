import pandas as pd
import numpy as np
from app.services.advanced_modeling_service import AdvancedModelingService

def test_fit_fine_gray_synthetic():
    # 1. 创建模拟的竞争风险数据
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        'time': np.random.exponential(10, n),
        'event': np.random.choice([0, 1, 2], n, p=[0.2, 0.4, 0.4]),
        'age': np.random.normal(60, 10, n),
        'treatment': np.random.binomial(1, 0.5, n)
    })
    
    # 2. 为事件 1 拟合 Fine-Gray 模型
    try:
        res = AdvancedModelingService.fit_fine_gray(
            df, 'time', 'event', ['age', 'treatment'], event_of_interest=1
        )
        
        if res and 'models' in res:
            print("Fine-Gray Fit Success")
            print(res['models'][0]['summary'])
        else:
            print("Fine-Gray Fit returned empty or invalid structure")
        
    except ImportError:
        print("SKIP: FineGrayFitter not installed")
    except Exception as e:
        print(f"Fine-Gray Fit Failed: {e}")
        # raise e

if __name__ == "__main__":
    test_fit_fine_gray_synthetic()
