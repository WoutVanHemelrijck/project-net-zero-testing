"""Example input file with real Python code to transform."""


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


def main_func(items, price):
    total = calculate_total_price(items, price)
    return format_result(total)
