import pytest
from app.strategies.service import validate_strategy
def test_strategy_validation(): assert validate_strategy({'fast':10,'slow':20}).fast==10
def test_reject_invalid_periods():
 with pytest.raises(ValueError): validate_strategy({'fast':30,'slow':20})
