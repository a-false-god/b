import sys
import io
import pytest

if __name__ == "__main__":
    # Run pytest with -v output
    buffer = io.StringIO()
    sys.stdout = buffer
    sys.stderr = buffer
    
    exit_code = pytest.main(["-v", "tests/"])
    
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    
    output = buffer.getvalue()
    with open("tests/pytest_output.txt", "w", encoding="utf-8") as f:
        f.write(output)
    
    print(output)
    print(f"Pytest Exit Code: {exit_code}")
