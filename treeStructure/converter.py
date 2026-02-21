#!/usr/bin/env python
"""
Converter: Transform any Python file.

Usage:
    python -m treeStructure.converter <input_file> [spec_file]
"""

import sys
from pathlib import Path

from treeStructure import transform_code


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    spec_file = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    if not input_file.exists():
        sys.exit(1)
    if spec_file and not spec_file.exists():
        sys.exit(1)
    
    with open(input_file, "r") as f:
        input_code = f.read()

    spec_code = ""
    if spec_file:
        with open(spec_file, "r") as f:
            spec_code = f.read()

    transform_code(input_code, return_result=True, spec_code=spec_code)


if __name__ == "__main__":
    main()
