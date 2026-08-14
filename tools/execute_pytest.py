#!/usr/bin/env python3
import pytest
import sys

def run_tests():
    print("--- RUNNING PYTEST SUITE ---")
    ret = pytest.main(["-v", "tests/"])
    print(f"--- PYTEST FINISHED WITH EXIT CODE: {ret} ---")
    return ret

if __name__ == "__main__":
    sys.exit(run_tests())
