
import pytest
import pandas as pd
from app.services.modeling_service import ModelingService
from app.services.preprocessing_service import PreprocessingService

@pytest.fixture
def singular_df(load_golden_dataset):
    return load_golden_dataset("edge_singular.csv")

@pytest.fixture
def gbk_df(load_golden_dataset):
    return load_golden_dataset("edge_encoding_gbk.csv", encoding='gbk')

def test_edge_singular_matrix(singular_df):
    """
    Test logic when perfect collinearity exists (x2 = 2 * x1).
    Should either raise a friendly error or handle it via regularization (if enabled).
    Currently expectation is ValueError with 'singular matrix' or 'perfect separation'.
    """
    # x1 and x2 are collinear
    # Match "Singular matrix" (case insensitive or exact)
    with pytest.raises(ValueError, match="Singular matrix"):
        ModelingService.run_model(singular_df, 'linear', 'y', ['x1', 'x2'])

def test_edge_gbk_encoding(gbk_df):
    """
    Test reading of GBK encoded file with Chinese characters.
    """
    # Verify Chinese headers are parsed correctly
    assert '姓名' in gbk_df.columns
    assert '备注' in gbk_df.columns
    
    # Verify content
    assert gbk_df.iloc[0]['姓名'] == '张三'
    
    # Test handling of "Not Known" (custom NA in generation script but pandas reads as string by default)
    # Just ensure it was read safely
    assert 'Not Known' in gbk_df['姓名'].values

