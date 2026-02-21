from __future__ import annotations
import ast
from pathlib import Path
from dataclasses import dataclass, field
import json
import networkx as nx


@dataclass
class TransformResult:
    """Mutable container holding original code, optimized code, and metadata.
    
    This object is returned when using transform_code(return_result=True).
    It allows inspection and modification of code transformations and dependency graphs.
    
    Attributes:
        original_code (str): The original, untransformed Python source code.
        optimized_code (str): The transformed code (functions wrapped in Node_<name> classes).
        is_optimized (bool): Flag to determine which code is returned by selected_code.
        dependencies (dict): Dependency graph: {function_name: [called_functions]}.
        execution_order (list): Topological sort of functions (leaf functions first).
        node_codes (dict): Per-node code mapping: {func_name: {"original": code, "optimized": code}}.
        spec_code (str): Optional spec file content containing test_* functions.
        test_mapping (dict): Mapping from function name to test function name.
        test_codes (dict): Mapping from function name to test function code.
    
    Example:
        >>> from treeStructure import transform_code
        >>> code = "def a():\\n    return b()\\ndef b():\\n    return 1"
        >>> result = transform_code(code, return_result=True)
        >>> result.get_original_code()  # Original input
        >>> result.get_optimized_code()  # Transformed with Node_ classes
        >>> result.get_dependencies()  # {'a': ['b'], 'b': []}
        >>> result.get_execution_order()  # ['b', 'a']
        >>> result.selected_code  # Returns optimized (is_optimized=True)
        >>> result.set_is_optimized(False)
        >>> result.selected_code  # Returns original
    """

    original_code: str
    optimized_code: str
    is_optimized: bool
    dependencies: dict[str, list[str]]
    execution_order: list[str]
    node_codes: dict[str, dict[str, str]] = field(default_factory=dict)
    spec_code: str = ""
    test_mapping: dict[str, str] = field(default_factory=dict)
    test_codes: dict[str, str] = field(default_factory=dict)

    @property
    def selected_code(self) -> str:
        """Return output based on the optimization flag."""
        return self.optimized_code if self.is_optimized else self.original_code

    def get_original_code(self) -> str:
        """Get the original source code."""
        return self.original_code

    def set_original_code(self, new_code: str) -> None:
        """Update the original source code."""
        self.original_code = new_code

    def get_optimized_code(self) -> str:
        """Get the optimized source code."""
        return self.optimized_code

    def set_optimized_code(self, new_code: str) -> None:
        """Update the optimized source code."""
        self.optimized_code = new_code

    def get_is_optimized(self) -> bool:
        """Get the optimization mode flag."""
        return self.is_optimized

    def set_is_optimized(self, value: bool) -> None:
        """Update the optimization mode flag."""
        self.is_optimized = value

    def get_dependencies(self) -> dict[str, list[str]]:
        """Get function dependency graph: {function_name: [called_functions]}."""
        return self.dependencies

    def get_execution_order(self) -> list[str]:
        """Get topological sort order for functions (leaf functions first)."""
        return self.execution_order

    def get_spec_code(self) -> str:
        """Get the spec file content."""
        return self.spec_code

    def set_spec_code(self, spec_code: str) -> None:
        """Update the spec file content."""
        self.spec_code = spec_code

    def get_test_mapping(self) -> dict[str, str]:
        """Get function-to-test mapping derived from the spec file."""
        return self.test_mapping

    def get_test_code(self, func_name: str) -> str | None:
        """Get test function code linked to a function, if available."""
        return self.test_codes.get(func_name)

    def to_json(self, include_full_code: bool = False) -> str:
        """Convert TransformResult to JSON for frontend transmission.
        
        Parameters:
            include_full_code (bool): If True, include full original_code and optimized_code.
                                     Node codes are always included.
        
        Returns:
            str: JSON representation with per-node code, dependencies, and execution order.
        
        Example:
            >>> result = transform_code(code, return_result=True)
            >>> json_str = result.to_json()
            >>> frontend_data = json.loads(json_str)
            >>> # frontend_data contains nodes with per-node code
        """
        # Build nodes list with per-node code
        depth_by_func = {
            func_name: index for index, func_name in enumerate(self.execution_order)
        }
        nodes = []
        for func_name in self.execution_order:
            node = {
                "id": func_name,
                "name": func_name,
                "depth": depth_by_func.get(func_name, 0),
                "depends_on": self.dependencies.get(func_name, []),
                "depended_by": [
                    caller
                    for caller, callees in self.dependencies.items()
                    if func_name in callees
                ],
                "original_code": self.node_codes.get(func_name, {}).get("original", ""),
                "optimized_code": self.node_codes.get(func_name, {}).get("optimized", ""),
                "test_name": self.test_mapping.get(func_name, ""),
                "test_code": self.test_codes.get(func_name, ""),
                "is_optimized": self.is_optimized,
            }
            nodes.append(node)

        edges = []
        seen_edges: set[tuple[str, str]] = set()
        for caller, callees in self.dependencies.items():
            for callee in callees:
                edge_key = (caller, callee)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                edges.append({"from": caller, "to": callee, "type": "calls"})

        leaf_functions = [
            func for func, deps in self.dependencies.items() if not deps
        ]
        max_depth = max(depth_by_func.values(), default=0)
        has_circular_dependencies = len(self.execution_order) == 0 and bool(
            self.dependencies
        )

        data = {
            "metadata": {
                "created_at": "2026-02-20T12:00:00Z",
                "version": "1.0",
                "language": "python",
            },
            "is_optimized": self.is_optimized,
            "statistics": {
                "total_functions": len(self.defined_functions),
                "total_dependencies": len(
                    [dep for deps in self.dependencies.values() for dep in deps]
                ),
                "max_depth": max_depth,
                "has_circular_dependencies": has_circular_dependencies,
                "leaf_functions": leaf_functions,
            },
            "nodes": nodes,
            "edges": edges,
            "execution_order": self.execution_order,
            "dependencies": self.dependencies,
        }
        
        if include_full_code:
            data["original_code"] = self.original_code
            data["optimized_code"] = self.optimized_code
            data["spec_code"] = self.spec_code
        
        return json.dumps(data, indent=2)

    @property
    def defined_functions(self) -> set[str]:
        """Get set of all defined function names."""
        return set(self.dependencies.keys())

    def get_node_code(self, func_name: str, optimized: bool = True) -> str | None:
        """Get code for a specific function node.
        
        Parameters:
            func_name (str): Name of the function/node.
            optimized (bool): If True, return optimized code; if False, return original.
        
        Returns:
            str: Code for the node, or None if not found.
        
        Example:
            >>> result = transform_code(code, return_result=True)
            >>> result.get_node_code("my_func", optimized=True)  # Get optimized version
            >>> result.get_node_code("my_func", optimized=False)  # Get original version
        """
        if func_name not in self.node_codes:
            return None
        code_pair = self.node_codes[func_name]
        return code_pair.get("optimized" if optimized else "original")


class DependencyVisitor(ast.NodeVisitor):
    """Collect function definitions and internal function-call dependencies."""

    def __init__(self) -> None:
        self.current_function: str | None = None
        self.dependencies: list[tuple[str, str]] = []
        self.defined_functions: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit and track function names and scan nested calls inside each function."""
        self.defined_functions.add(node.name)
        previous_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = previous_function

    def visit_Call(self, node: ast.Call) -> None:
        """Capture calls from one function to another (excluding self-calls)."""
        if isinstance(node.func, ast.Name):
            called_name = node.func.id
            if self.current_function and called_name != self.current_function:
                self.dependencies.append((self.current_function, called_name))
        self.generic_visit(node)


class CodeRefactorer(ast.NodeTransformer):
    """Wrap each top-level function node in a class named `Node_<function>`."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.ClassDef:
        return ast.ClassDef(
            name=f"Node_{node.name}",
            bases=[],
            keywords=[],
            body=[node],
            decorator_list=[],
        )


def transform_code(
    source_code: str,
    is_optimized: bool = True,
    return_result: bool = False,
    spec_code: str | None = None,
) -> str | TransformResult:
    """Transform Python functions into class-wrapped nodes ordered by dependency depth.
    
    Analyzes source code to extract function definitions and their call dependencies,
    computes a topological sort (leaf functions first), detects circular dependencies,
    and optionally wraps each function in a Node_<function_name> class.
    
    Parameters:
        source_code (str): Valid Python source code containing function definitions.
        is_optimized (bool, default=True): If True, return transformed code; if False, return original.
        return_result (bool, default=False): If True, return TransformResult object with all data;
                                            if False, return only the code string.
        spec_code (str, optional): Spec file content with test_<function> definitions.
    
    Returns:
        str: The selected code (original or optimized) if return_result=False.
        TransformResult: Object containing original_code, optimized_code, is_optimized,
                        dependencies, and execution_order if return_result=True.
    
    Raises:
        SyntaxError: If source_code is not valid Python.
        Any error from ast.parse: For malformed Python.
    
    Example (Basic):
        >>> code = '''
        ... def b():
        ...     return 1
        ... def a():
        ...     return b()
        ... '''
        >>> result = transform_code(code)
        >>> "class Node_a:" in result
        True
        >>> "class Node_b:" in result
        True
    
    Example (With Dependency Inspection):
        >>> result = transform_code(code, return_result=True)
        >>> result.get_dependencies()
        {'a': ['b'], 'b': []}
        >>> result.get_execution_order()
        ['b', 'a']
        >>> result.selected_code  # optimized code by default
        'class Node_b:\\n    def b():\\n        return 1\\n\\nclass Node_a:\\n...'
        >>> result.set_is_optimized(False)
        >>> result.selected_code  # now original code
        '\\ndef b():\\n    return 1\\ndef a():\\n    return b()\\n'
    
    Example (Circular Dependency Detection):
        >>> circular = '''
        ... def a():
        ...     return b()
        ... def b():
        ...     return a()
        ... '''
        >>> result = transform_code(circular)
        >>> result
        'Fout: Er zit een circulaire afhankelijkheid in de functies.'
    
    Notes:
        - Non-function nodes (imports, global variables) are preserved at the top.
        - Self-calls (recursive calls) are ignored in the dependency graph.
        - The execution_order guarantees that dependencies come before dependents.
    """
    tree = ast.parse(source_code)
    spec_tree = ast.parse(spec_code) if spec_code else None

    visitor = DependencyVisitor()
    visitor.visit(tree)

    valid_dependencies = [
        (caller, callee)
        for caller, callee in visitor.dependencies
        if callee in visitor.defined_functions
    ]

    graph = nx.DiGraph()
    graph.add_nodes_from(visitor.defined_functions)
    graph.add_edges_from(valid_dependencies)

    # Build dependency dict for user inspection
    dependencies_dict = {
        func: [callee for caller, callee in valid_dependencies if caller == func]
        for func in visitor.defined_functions
    }

    function_nodes = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    other_nodes = [node for node in tree.body if not isinstance(node, ast.FunctionDef)]

    test_mapping: dict[str, str] = {}
    test_codes: dict[str, str] = {}
    if spec_tree:
        spec_test_nodes = {
            node.name: node
            for node in spec_tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        }
        spec_tests = set(spec_test_nodes.keys())
        for func_name in function_nodes.keys():
            test_name = f"test_{func_name}"
            if test_name in spec_tests:
                test_mapping[func_name] = test_name
                test_codes[func_name] = ast.unparse(spec_test_nodes[test_name])

    try:
        execution_order = list(nx.topological_sort(graph))[::-1]
    except nx.NetworkXUnfeasible:
        optimized_code = "Fout: Er zit een circulaire afhankelijkheid in de functies."
        result = TransformResult(
            original_code=source_code,
            optimized_code=optimized_code,
            is_optimized=is_optimized,
            dependencies=dependencies_dict,
            execution_order=[],
            node_codes={},
            spec_code=spec_code or "",
            test_mapping=test_mapping,
            test_codes=test_codes,
        )
        return result if return_result else result.selected_code

    transformer = CodeRefactorer()

    # Build node_codes dict: {func_name: {original: code, optimized: code}}
    node_codes: dict[str, dict[str, str]] = {}
    transformed_nodes = []
    
    for function_name in execution_order:
        original_node = function_nodes[function_name]
        optimized_node = transformer.visit(original_node)
        
        # Extract per-node code
        original_func_code = ast.unparse(original_node)
        optimized_func_code = ast.unparse(optimized_node)
        
        node_codes[function_name] = {
            "original": original_func_code,
            "optimized": optimized_func_code,
        }
        
        transformed_nodes.append(optimized_node)

    tree.body = other_nodes + transformed_nodes
    optimized_code = ast.unparse(tree)

    result = TransformResult(
        original_code=source_code,
        optimized_code=optimized_code,
        is_optimized=is_optimized,
        dependencies=dependencies_dict,
        execution_order=execution_order,
        node_codes=node_codes,
        spec_code=spec_code or "",
        test_mapping=test_mapping,
        test_codes=test_codes,
    )
    return result if return_result else result.selected_code


def write_optimized_file(result: TransformResult, input_file_path: str | Path) -> Path:
    """Write optimized code to optimized_<input_file> or fall back to original.

    Parameters:
        result (TransformResult): Result with optimized/original code.
        input_file_path (str | Path): Original input file path.

    Returns:
        Path: Path to the written output file.
    """
    input_path = Path(input_file_path)
    output_path = input_path.with_name(f"optimized_{input_path.name}")
    code = result.optimized_code if result.optimized_code.strip() else result.original_code
    output_path.write_text(code, encoding="utf-8")
    return output_path