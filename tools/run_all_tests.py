#!/usr/bin/env python3
import sys
import pytest

if __name__ == "__main__":
    ret = pytest.main(["-v", "tests/"])
    sys.exit(ret)
