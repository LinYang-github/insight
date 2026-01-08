import pytest
import pandas as pd
import numpy as np
import os
import json
from app.services.data_service import DataService

class TestDataService:

    def test_sanitize_for_json_basics(self):
        """Test basic types pass through."""
        obj = {"a": 1, "b": "text", "c": 1.5, "d": None, "e": True}
        sanitized = DataService.sanitize_for_json(obj)
        assert sanitized == obj

    def test_sanitize_for_json_nan_inf(self):
        """Test NaN and Inf converting to None."""
        obj = {
            "nan": float('nan'),
            "inf": float('inf'),
            "neg_inf": float('-inf'),
            "nested": [float('nan')]
        }
        sanitized = DataService.sanitize_for_json(obj)
        assert sanitized["nan"] is None
        assert sanitized["inf"] is None
        assert sanitized["neg_inf"] is None
        assert sanitized["nested"][0] is None

    def test_sanitize_for_json_numpy_types(self):
        """Test numpy types converting to Python primitives."""
        obj = {
            "np_int": np.int64(42),
            "np_float": np.float64(3.14),
            "np_nan": np.nan,
            "np_inf": np.inf
        }
        sanitized = DataService.sanitize_for_json(obj)
        
        # Check types
        assert isinstance(sanitized["np_int"], int) 
        assert sanitized["np_int"] == 42
        
        assert isinstance(sanitized["np_float"], float)
        assert abs(sanitized["np_float"] - 3.14) < 1e-9
        
        assert sanitized["np_nan"] is None
        assert sanitized["np_inf"] is None

    def test_read_csv_encoding_utf8(self, tmp_path):
        """Test reading UTF-8 CSV."""
        filepath = tmp_path / "utf8.csv"
        df = pd.DataFrame({"col1": ["中文", "English"]})
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        result = DataService.get_initial_metadata(str(filepath))
        assert result['row_count'] == 2
        assert result['variables'][0]['name'] == 'col1'

    def test_read_csv_encoding_gb18030(self, tmp_path):
        """Test reading GB18030 CSV."""
        filepath = tmp_path / "gbk.csv"
        # Manually write bytes for GBK content
        with open(filepath, 'wb') as f:
            content = "变量,数值\n测试,100".encode('gb18030')
            f.write(content)
            
        result = DataService.get_initial_metadata(str(filepath))
        assert result['row_count'] == 1
        # Check if column names are correctly decoded
        names = [v['name'] for v in result['variables']]
        assert "变量" in names
        assert "数值" in names

    def test_read_csv_fallback_latin1(self, tmp_path):
        """Test fallback to latin1 for weird binary data."""
        filepath = tmp_path / "weird.csv"
        # Write some random bytes that are invalid utf-8 and invalid gbk
        # Latin1 should accept any byte value 0-255
        with open(filepath, 'wb') as f:
            f.write(b"col1\n\x80\xff") 
            
        result = DataService.get_initial_metadata(str(filepath))
        assert result['row_count'] == 1
