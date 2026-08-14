import sys
import io
import pytest

def main():
    buffer = io.StringIO()
    sys.stdout = buffer
    sys.stderr = buffer

    ret = pytest.main(["-v", "tests/"])

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    output = buffer.getvalue()
    with open("tests/pytest_report.txt", "w", encoding="utf-8") as f:
        f.write(output)

    print("Pytest output captured. Exit code:", ret)

if __name__ == "__main__":
    main()
