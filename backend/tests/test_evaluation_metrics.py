import numpy as np
import pandas as pd
from app.services.evaluation_service import EvaluationService

class TestEvaluationService:
    
    def assert_approx(self, actual, expected, tol=0.01):
        assert abs(actual - expected) < tol, f"预期值 {expected}, 实际值 {actual}"

    def test_nri_perfect_improvement(self):
        """
        [测试用例 1] 完美改善 (Perfect Improvement)
        逻辑：
        - 真实标签 y_true: [1, 1, 0, 0] (2个事件, 2个非事件)
        - 旧模型 p_old: 都是 0.5 (瞎猜)
        - 新模型 p_new: 
            - Event组 (1,1): 预测概率从 0.5 提升到 0.6 和 0.9 (全部变好)，P(up|event) = 1.0
            - Non-Event组 (0,0): 预测概率从 0.5 降低到 0.4 和 0.1 (全部变好)，P(down|nonevent) = 1.0
        - NRI = P(up|event) - P(down|event) + P(down|nonevent) - P(up|nonevent)
              = (1 - 0) + (1 - 0) = 2.0
        预期结果：NRI 应该等于理论最大值 2.0
        """
        y_true = np.array([1, 1, 0, 0])
        p_old = np.array([0.5, 0.5, 0.5, 0.5])
        p_new = np.array([0.6, 0.9, 0.4, 0.1])
        
        res = EvaluationService.calculate_nri_idi(y_true, p_old, p_new)
        print(f"\n[Perfect Case] NRI: {res['nri']}")
        self.assert_approx(res['nri'], 2.0)
        
    def test_nri_no_change(self):
        """
        [测试用例 2] 无变化 (No Change)
        逻辑：新旧模型预测概率完全一致。
        预期结果：NRI = 0.0
        """
        y_true = np.array([1, 1, 0, 0])
        p_old = np.array([0.6, 0.6, 0.4, 0.4])
        p_new = np.array([0.6, 0.6, 0.4, 0.4])
        
        res = EvaluationService.calculate_nri_idi(y_true, p_old, p_new)
        print(f"\n[No Change Case] NRI: {res['nri']}")
        self.assert_approx(res['nri'], 0.0)

    def test_nri_mixed_case(self):
        """
        [测试用例 3] 混合情况 (Mixed Case) - 模拟真实场景
        逻辑：
        - y_true: 4个事件, 4个非事件
        - Event组 (4人): 3人概率升高(好), 1人概率降低(坏) -> P(up|e)=0.75, P(down|e)=0.25 -> NRI_e = 0.5
        - Non-Event组 (4人): 2人概率降低(好), 2人概率升高(坏) -> P(down|ne)=0.5, P(up|ne)=0.5 -> NRI_ne = 0
        - 总 NRI = 0.5 + 0 = 0.5
        预期结果：NRI = 0.5
        """
        y_true = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        p_old = np.full(8, 0.5)
        p_new = np.array([
            0.6, 0.7, 0.8, 0.4, # Event组: 升, 升, 升, 降
            0.4, 0.3, 0.6, 0.7  # Non-Event组: 降, 降, 升, 升
        ])
        
        res = EvaluationService.calculate_nri_idi(y_true, p_old, p_new)
        print(f"\n[Mixed Case] NRI: {res['nri']}")
        self.assert_approx(res['nri'], 0.5)

    def test_idi_calculation(self):
        """
        [测试用例 4] IDI 计算 (Integrated Discrimination Improvement)
        逻辑：
        - IDI = (Mean_new_event - Mean_old_event) - (Mean_new_nonevent - Mean_old_nonevent)
        - Event组: (0.7 - 0.5) = +0.2 (提升)
        - Non-Event组: (0.3 - 0.5) = -0.2 (降低，是好事)
        - IDI = 0.2 - (-0.2) = 0.4
        预期结果：IDI = 0.4
        """
        y_true = np.array([1, 0])
        p_old = np.array([0.5, 0.5])
        p_new = np.array([0.7, 0.3])
        
        res = EvaluationService.calculate_nri_idi(y_true, p_old, p_new)
        print(f"\n[IDI Case] IDI: {res['idi']}")
        self.assert_approx(res['idi'], 0.4)

    def test_delong_identical(self):
        """
        [测试用例 5] Delong Test 稳健性测试
        逻辑：测试当两个模型完全一致时，算法是否会崩溃 (除以零)。
        预期结果：P值应为 1.0 (无差异)，Z值应为 0。
        """
        y_true = np.array([1, 0, 1, 0, 1])
        p_base = np.array([0.8, 0.2, 0.7, 0.3, 0.9])
        p_new = p_base.copy()
        
        res = EvaluationService.calculate_delong_test(y_true, p_base, p_new)
        print(f"\n[Delong Identical] P-val: {res['p_delong']}")
        
        # Z-score should be 0, P-value 1.0 (or close to 1)
        assert res['z_delong'] == 0.0 or res['p_delong'] > 0.99

if __name__ == "__main__":
    t = TestEvaluationService()
    try:
        t.test_nri_perfect_improvement()
        t.test_nri_no_change()
        t.test_nri_mixed_case()
        t.test_idi_calculation()
        t.test_delong_identical()
        print("\n✅ 所有单元测试通过！统计逻辑验证无误 (All unit tests passed).")
    except AssertionError as e:
        print(f"\n❌ 测试失败 (Test Failed): {e}")
    except Exception as e:
        print(f"\n❌ 意外错误 (Unexpected Error): {e}")
