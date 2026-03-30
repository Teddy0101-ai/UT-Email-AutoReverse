import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from run import main

if __name__ == "__main__":
    main()