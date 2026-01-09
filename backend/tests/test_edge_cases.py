
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

def test_edge_high_collinearity(load_golden_dataset):
    """
    Test soft collinearity (r > 0.99).
    Models often still run but with high variance.
    We just ensure it doesn't crash the server.
    """
    df = load_golden_dataset("edge_collinear.csv")
    # Should run without error, or warn
    try:
        ModelingService.run_model(df, 'linear', 'y', ['x1', 'x2'])
    except Exception as e:
        pytest.fail(f"High collinearity caused crash: {e}")

def test_edge_all_nan(load_golden_dataset):
    """
    Test completely NaN dataset.
    Should raise ValueError during modeling or preprocessing.
    """
    df = load_golden_dataset("edge_all_nan.csv")
    # All are NaN, so dropna will result in empty DF.
    # ModelingService usually checks for empty DF.
    with pytest.raises(ValueError):
         ModelingService.run_model(df, 'linear', 'A', ['B'])

