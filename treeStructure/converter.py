#!/usr/bin/env python
"""
Converter: Transform any Python file.

Usage:
    python -m treeStructure.converter <input_file>
"""

import sys
from pathlib import Path

from treeStructure import transform_code


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if not input_file.exists():
        sys.exit(1)
    
    with open(input_file, "r") as f:
        input_code = f.read()

    transform_code(input_code, return_result=True)


if __name__ == "__main__":
    main()
