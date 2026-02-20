import textwrap

from treeStructure import TransformResult, transform_code


def test_transform_wraps_functions_in_node_classes() -> None:
    source = textwrap.dedent(
        """
        def a():
            return b() + c()

        def b():
            return 10

        def c():
            return d()

        def d():
            return 5
        """
    )

    result = transform_code(source)

    assert "class Node_a:" in result
    assert "class Node_b:" in result
    assert "class Node_c:" in result
    assert "class Node_d:" in result


def test_transform_keeps_non_function_nodes_at_top() -> None:
    source = textwrap.dedent(
        """
        import math
        GLOBAL_VALUE = 42

        def a():
            return b()

        def b():
            return 1
        """
    )

    result = transform_code(source)

    assert result.startswith("import math\nGLOBAL_VALUE = 42")


def test_transform_returns_error_on_circular_dependencies() -> None:
    source = textwrap.dedent(
        """
        def a():
            return b()

        def b():
            return a()
        """
    )

    result = transform_code(source)

    assert result == "Fout: Er zit een circulaire afhankelijkheid in de functies."


def test_transform_returns_original_when_not_optimized() -> None:
    source = textwrap.dedent(
        """
        def a():
            return b()

        def b():
            return 1
        """
    )

    result = transform_code(source, is_optimized=False)

    assert result == source


def test_transform_can_return_original_and_optimized_in_result() -> None:
    source = textwrap.dedent(
        """
        def a():
            return b()

        def b():
            return 1
        """
    )

    result = transform_code(source, is_optimized=True, return_result=True)

    assert isinstance(result, TransformResult)
    assert result.original_code == source
    assert "class Node_a:" in result.optimized_code
    assert "class Node_b:" in result.optimized_code
    assert result.selected_code == result.optimized_code
    assert "a" in result.dependencies
    assert "b" in result.dependencies
    assert result.get_execution_order() is not None


def test_transform_result_fields_can_be_read_and_updated() -> None:
    result = TransformResult(
        original_code="print('old')",
        optimized_code="print('new')",
        is_optimized=True,
        dependencies={"func_a": ["func_b"]},
        execution_order=["func_b", "func_a"],
    )

    assert result.get_original_code() == "print('old')"
    assert result.get_optimized_code() == "print('new')"
    assert result.get_is_optimized() is True
    assert result.get_dependencies() == {"func_a": ["func_b"]}
    assert result.get_execution_order() == ["func_b", "func_a"]

    result.set_original_code("print('old-updated')")
    result.set_optimized_code("print('new-updated')")
    result.set_is_optimized(False)

    assert result.original_code == "print('old-updated')"
    assert result.optimized_code == "print('new-updated')"
    assert result.is_optimized is False
    assert result.selected_code == "print('old-updated')"


def test_transform_result_includes_dependency_graph_and_execution_order() -> None:
    source = textwrap.dedent(
        """
        def d():
            return 5

        def c():
            return d()

        def b():
            return 10

        def a():
            return b() + c()
        """
    )

    result = transform_code(source, return_result=True)

    assert isinstance(result, TransformResult)
    deps = result.get_dependencies()
    order = result.get_execution_order()

    assert "a" in deps
    assert "b" in deps
    assert "c" in deps
    assert "d" in deps
    assert deps["a"] == ["b", "c"]
    assert deps["c"] == ["d"]
    assert len(order) == 4
    # d should come before c, c and b before a
    assert order.index("d") < order.index("c")
    assert order.index("b") < order.index("a")
    assert order.index("c") < order.index("a")


# === Edge cases ===


def test_transform_single_function_no_dependencies() -> None:
    source = textwrap.dedent(
        """
        def standalone():
            return 42
        """
    )

    result = transform_code(source)

    assert "class Node_standalone:" in result
    assert "return 42" in result


def test_transform_multiple_independent_functions() -> None:
    source = textwrap.dedent(
        """
        def func1():
            return 1

        def func2():
            return 2

        def func3():
            return 3
        """
    )

    result = transform_code(source, return_result=True)

    assert isinstance(result, TransformResult)
    assert len(result.get_execution_order()) == 3
    assert all(f in result.get_dependencies() for f in ["func1", "func2", "func3"])


def test_transform_linear_chain_dependencies() -> None:
    source = textwrap.dedent(
        """
        def e():
            return 5

        def d():
            return e()

        def c():
            return d()

        def b():
            return c()

        def a():
            return b()
        """
    )

    result = transform_code(source, return_result=True)

    order = result.get_execution_order()
    # e must come first, a last in linear chain
    assert order.index("e") < order.index("d")
    assert order.index("d") < order.index("c")
    assert order.index("c") < order.index("b")
    assert order.index("b") < order.index("a")


def test_transform_branching_dependencies() -> None:
    source = textwrap.dedent(
        """
        def leaf1():
            return 10

        def leaf2():
            return 20

        def leaf3():
            return 30

        def middle():
            return leaf1() + leaf2()

        def root():
            return middle() + leaf3()
        """
    )

    result = transform_code(source, return_result=True)

    deps = result.get_dependencies()
    assert deps["middle"] == ["leaf1", "leaf2"]
    assert set(deps["root"]) == {"middle", "leaf3"}
    assert all(leaf in deps["middle"] for leaf in ["leaf1", "leaf2"])


def test_transform_with_multiple_globals_and_imports() -> None:
    source = textwrap.dedent(
        """
        import sys
        from os import path

        CONSTANT_A = 100
        CONSTANT_B = 200

        def helper():
            return CONSTANT_A

        def main():
            return helper() + CONSTANT_B
        """
    )

    result = transform_code(source)

    assert result.startswith("import sys\nfrom os import path")
    assert "CONSTANT_A" in result
    assert "CONSTANT_B" in result
    assert "class Node_helper:" in result
    assert "class Node_main:" in result


def test_transform_function_with_multiple_parameters() -> None:
    source = textwrap.dedent(
        """
        def add(x, y):
            return x + y

        def multiply(a, b):
            return a * b

        def compute():
            return add(1, 2) + multiply(3, 4)
        """
    )

    result = transform_code(source)

    assert "class Node_add:" in result
    assert "class Node_multiply:" in result
    assert "class Node_compute:" in result


def test_transform_self_calls_ignored() -> None:
    source = textwrap.dedent(
        """
        def recursive_func(n):
            if n <= 0:
                return 1
            return n * recursive_func(n - 1)
        """
    )

    result = transform_code(source, return_result=True)

    # Self-calls should not create dependency
    assert result.get_dependencies()["recursive_func"] == []


def test_transform_empty_function() -> None:
    source = textwrap.dedent(
        """
        def empty():
            pass

        def caller():
            return empty()
        """
    )

    result = transform_code(source)

    assert "class Node_empty:" in result
    assert "class Node_caller:" in result
    assert "pass" in result


def test_transform_function_with_multiple_calls_same_function() -> None:
    source = textwrap.dedent(
        """
        def helper():
            return 5

        def caller():
            x = helper()
            y = helper()
            return x + y
        """
    )

    result = transform_code(source, return_result=True)

    deps = result.get_dependencies()
    # helper is called twice, so it appears twice in dependency list
    assert deps["caller"].count("helper") == 2


def test_transform_return_result_with_optimized_false() -> None:
    source = textwrap.dedent(
        """
        def a():
            return b()

        def b():
            return 1
        """
    )

    result = transform_code(source, is_optimized=False, return_result=True)

    assert isinstance(result, TransformResult)
    assert result.original_code == source
    assert result.selected_code == source  # should return original, not optimized


def test_transform_circular_dependency_in_result() -> None:
    source = textwrap.dedent(
        """
        def x():
            return y()

        def y():
            return x()
        """
    )

    result = transform_code(source, return_result=True)

    assert isinstance(result, TransformResult)
    assert "Fout: Er zit een circulaire afhankelijkheid in de functies." in result.selected_code
    assert result.execution_order == []


def test_transform_complex_diamond_dependency() -> None:
    source = textwrap.dedent(
        """
        def d():
            return 4

        def b():
            return d()

        def c():
            return d()

        def a():
            return b() + c()
        """
    )

    result = transform_code(source, return_result=True)

    deps = result.get_dependencies()
    order = result.get_execution_order()

    # d is called by both b and c
    assert deps["b"] == ["d"]
    assert deps["c"] == ["d"]
    assert deps["a"] == ["b", "c"]
    # d should come first as it's a leaf
    assert order.index("d") < order.index("b")
    assert order.index("d") < order.index("c")
    assert order.index("b") < order.index("a")
    assert order.index("c") < order.index("a")


def test_transform_preserves_code_comments_and_docstrings() -> None:
    source = textwrap.dedent(
        '''
        def helper():
            """Helper docstring."""
            # This is a comment
            return 42

        def main():
            # Call helper
            return helper()
        '''
    )

    result = transform_code(source)

    assert 'Helper docstring' in result
    assert 'class Node_helper:' in result
    assert 'class Node_main:' in result


def test_transform_result_mutation_pattern() -> None:
    source = "def a():\n    return 1"
    result = transform_code(source, return_result=True)

    original_deps = result.get_dependencies().copy()
    original_order = result.get_execution_order().copy()

    # Mutate dependencies
    result.dependencies["new_func"] = ["a"]
    assert "new_func" in result.get_dependencies()

    # Mutate execution order
    result.execution_order.append("new_func")
    assert "new_func" in result.get_execution_order()


def test_transform_string_representation_consistency() -> None:
    source = textwrap.dedent(
        """
        def inner():
            return 10

        def outer():
            return inner()
        """
    )

    result1 = transform_code(source, is_optimized=True, return_result=True)
    result2 = transform_code(source, is_optimized=True, return_result=True)

    # Same input should produce same transformation
    assert result1.optimized_code == result2.optimized_code
    assert result1.get_dependencies() == result2.get_dependencies()
    assert result1.get_execution_order() == result2.get_execution_order()


def test_transform_large_codebase() -> None:
    functions = "\n\n".join(
        f"""def func{i}():
    return func{i - 1}() if {i} > 0 else {i}"""
        for i in range(10)
    )
    source = functions

    result = transform_code(source, return_result=True)

    assert len(result.get_execution_order()) == 10
    assert len(result.get_dependencies()) == 10


def test_transform_whitespace_handling() -> None:
    source = textwrap.dedent(
        """


        def a():
            return b()


        def b():
            return 1


        """
    )

    result = transform_code(source)

    assert "class Node_a:" in result
    assert "class Node_b:" in result


def test_transform_result_selected_code_switches_on_flag() -> None:
    source = "def a():\n    return 1"
    result = transform_code(source, is_optimized=True, return_result=True)

    # Initial state: optimized
    optimized_selected = result.selected_code
    assert "class Node_a:" in optimized_selected

    # Switch to non-optimized
    result.set_is_optimized(False)
    non_optimized_selected = result.selected_code
    assert non_optimized_selected == source
    assert "class Node_a:" not in non_optimized_selected

    # Switch back
    result.set_is_optimized(True)
    assert result.selected_code == optimized_selected


def test_transform_underscore_function_names() -> None:
    source = textwrap.dedent(
        """
        def _private():
            return 1

        def __dunder__():
            return _private()

        def public():
            return __dunder__()
        """
    )

    result = transform_code(source)

    assert "class Node__private:" in result
    assert "class Node___dunder__:" in result
    assert "class Node_public:" in result


def test_transform_result_json_serialization_with_node_codes() -> None:
    source = textwrap.dedent(
        """
        def b():
            return 1

        def a():
            return b()
        """
    )

    result = transform_code(source, return_result=True)
    json_str = result.to_json(include_full_code=False)
    
    assert json_str is not None
    data = __import__("json").loads(json_str)
    
    assert "nodes" in data
    assert len(data["nodes"]) == 2
    assert all("original_code" in node for node in data["nodes"])
    assert all("optimized_code" in node for node in data["nodes"])
    assert all("is_optimized" in node for node in data["nodes"])


def test_get_node_code_returns_correct_versions() -> None:
    source = textwrap.dedent(
        """
        def helper():
            return 42

        def main():
            return helper()
        """
    )

    result = transform_code(source, return_result=True)
    
    original_helper = result.get_node_code("helper", optimized=False)
    optimized_helper = result.get_node_code("helper", optimized=True)
    
    assert original_helper is not None
    assert optimized_helper is not None
    assert "def helper():" in original_helper
    assert "class Node_helper:" in optimized_helper
    assert result.get_node_code("nonexistent") is None


def test_integration_real_world_code_transformation_with_output() -> None:
    """Integration test: Transform a real-world Python file and display full output."""
    
    # Real-world example: calculator with dependencies
    real_world_code = textwrap.dedent(
        """
        def add(a, b):
            return a + b

        def multiply(x, y):
            return x * y

        def calculate_sum(numbers):
            total = 0
            for num in numbers:
                total = add(total, num)
            return total

        def calculate_total_price(quantities, unit_price):
            total_qty = calculate_sum(quantities)
            return multiply(total_qty, unit_price)

        def format_result(value):
            return f"Result: {value}"

        def main(items, price):
            total = calculate_total_price(items, price)
            return format_result(total)
        """
    )
    
    print("\n" + "="*80)
    print("INTEGRATION TEST: Real-World Python File Transformation")
    print("="*80)
    
    # Transform with result object
    result = transform_code(real_world_code, return_result=True)
    
    print("\n--- INPUT CODE ---")
    print(real_world_code)
    
    print("\n--- DEPENDENCIES GRAPH ---")
    deps = result.get_dependencies()
    for func, calls in deps.items():
        if calls:
            print(f"  {func} calls: {calls}")
        else:
            print(f"  {func} [leaf function]")
    
    print("\n--- EXECUTION ORDER (Topological Sort) ---")
    print("  " + " → ".join(result.get_execution_order()))
    
    print("\n--- STATISTICS ---")
    print(f"  Total functions: {len(result.defined_functions)}")
    print(f"  Leaf functions: {[f for f, calls in deps.items() if not calls]}")
    
    print("\n--- PER-NODE CODE (Original vs Optimized) ---")
    for func_name in result.get_execution_order():
        print(f"\n  ### {func_name.upper()} ###")
        original = result.get_node_code(func_name, optimized=False)
        optimized = result.get_node_code(func_name, optimized=True)
        
        print(f"\n  ORIGINAL:\n{textwrap.indent(original, '    ')}")
        print(f"\n  OPTIMIZED:\n{textwrap.indent(optimized, '    ')}")
    
    print("\n--- FULL OPTIMIZED CODE ---")
    print(result.get_optimized_code())
    
    print("\n--- JSON OUTPUT ---")
    json_output = result.to_json(include_full_code=True)
    print(json_output)
    
    # Assertions
    assert result is not None
    assert len(result.get_execution_order()) == 6
    assert "main" in deps
    assert "add" in deps
    assert not deps["add"]  # add is a leaf
    assert "calculate_total_price" in deps["main"]
    
    print("\n" + "="*80)
    print("✓ Integration test passed!")
    print("="*80 + "\n")
