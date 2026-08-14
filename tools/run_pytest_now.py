import pytest

print("============================= test session starts =============================")
ret = pytest.main(["-v", "tests/test_m7_m8_mastery.py"])
print("============================ test session ends ================================")
