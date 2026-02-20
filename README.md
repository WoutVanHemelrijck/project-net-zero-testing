# project-net-zero-testing

Python utility for analyzing function dependencies and transforming functions into class-based nodes.

## What does it do?

`treeStructure` parses Python code, builds a **dependency graph** of functions, detects **circular dependencies**, and orders functions **topologically** (leaf functions first). Optionally wraps each function in a `Node_<function>` class for node-based processing.

## Installation

1. Clone the repository:

```bash
git clone <your-repo-url>
cd project-net-zero-testing
```

2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:

- **Windows:** `venv\Scripts\activate`
- **macOS/Linux:** `source venv/bin/activate`

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Basic: Transform code

```python
from treeStructure import transform_code

code = """
def helper():
    return 10

def main():
    return helper() + 5
"""

result = transform_code(code)
print(result)
# Output: class-based nodes
```

### Advanced: Inspect dependency graph

```python
from treeStructure import transform_code

code = """
def d():
    return 5

def c():
    return d()

def b():
    return 10

def a():
    return b() + c()
"""

# Get everything: code + graph structure
result = transform_code(code, return_result=True)

# View dependency graph
print(result.get_dependencies())
# {'a': ['b', 'c'], 'b': [], 'c': ['d'], 'd': []}

# Execution order (topological)
print(result.get_execution_order())
# ['d', 'b', 'c', 'a']
```

### Get original code back

```python
result = transform_code(code, is_optimized=False)
# Returns original code without transformation
```

### Dynamic modifications

```python
result = transform_code(code, return_result=True)

# Modify code
result.set_optimized_code("# my custom code")

# Toggle mode
result.set_is_optimized(False)
print(result.selected_code)  # original
```

## API Reference

### `transform_code(source_code, is_optimized=True, return_result=False)`

**Parameters:**

- `source_code` (str): Python code.
- `is_optimized` (bool): Return transformed (True) or original code (False).
- `return_result` (bool): Return string (False) or TransformResult object (True).

**Returns:**

- `str | TransformResult`: Code or result object.

**Error Handling:**

- Detects circular dependencies and returns error message.

### `TransformResult` Object

**Fields:**

- `original_code`: Original input code
- `optimized_code`: Transformed code
- `is_optimized`: Current mode
- `dependencies`: Dict of dependencies
- `execution_order`: Topological ordering

**Methods:**

- `get_original_code()`, `set_original_code(code)`
- `get_optimized_code()`, `set_optimized_code(code)`
- `get_is_optimized()`, `set_is_optimized(value)`
- `get_dependencies()`, `get_execution_order()`
- `selected_code` (property): Returns correct code based on flag

## Tests

```bash
pytest  # 26+ tests with full coverage
```

## Structure

```
treeStructure/
├── __init__.py          # Public exports
├── treeStructure.py     # Core logic
└── tests/
    ├── conftest.py      # Test setup
    └── test_tree_structure.py  # 26+ tests
```

## Getting Started

You don't need to understand the implementation. Simply import `transform_code` and `TransformResult` and use them as shown in the examples. Docstrings in code help via IDE autocomplete.

Questions? Check tests for more examples.
