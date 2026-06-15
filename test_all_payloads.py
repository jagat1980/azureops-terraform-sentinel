import sys
import os

# Redirect execution to the new modular tests/run_all.py runner to preserve backward compatibility
if __name__ == "__main__":
    tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    sys.path.insert(0, tests_dir)
    from run_all import run_all_tests
    run_all_tests()
