#!/usr/bin/env python3
"""Simple tool: paste code → get string with visible \n"""

def code_to_escaped_string(code):
    """Convert code to string format with \\n visible."""
    escaped = code.replace('\\', '\\\\')
    escaped = escaped.replace('\n', '\\n')
    escaped = escaped.replace('\t', '\\t')
    escaped = escaped.replace('\r', '\\r')
    return escaped


# Input code
print("📝 Voer je code in (typ 'END' op nieuwe regel):")
print("-" * 60)
lines = []
while True:
    line = input()
    if line.strip() == "END":
        break
    lines.append(line)

code = "\n".join(lines)

# Output string format
escaped = code_to_escaped_string(code)
print("\n" + "=" * 60)
print("✅ STRING OUTPUT (met \\n zichtbaar):")
print("=" * 60)
print(escaped)
print("=" * 60)
