from __future__ import annotations
import ast
from dataclasses import dataclass
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
        )
        return result if return_result else result.selected_code

    transformer = CodeRefactorer()
    function_nodes = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    other_nodes = [node for node in tree.body if not isinstance(node, ast.FunctionDef)]

    transformed_nodes = [
        transformer.visit(function_nodes[function_name])
        for function_name in execution_order
    ]

    tree.body = other_nodes + transformed_nodes
    optimized_code = ast.unparse(tree)

    result = TransformResult(
        original_code=source_code,
        optimized_code=optimized_code,
        is_optimized=is_optimized,
        dependencies=dependencies_dict,
        execution_order=execution_order,
    )
    return result if return_result else result.selected_code