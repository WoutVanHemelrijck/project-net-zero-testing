#!/usr/bin/env python3
"""Simple tool: paste code → get string with visible \n"""

import json

print("📝 Voer je code in (typ 'END' op nieuwe regel):")
print("-" * 60)
lines = []
while True:
    line = input()
    if line.strip() == "END":
        break
    lines.append(line)

code = "\n".join(lines)

escaped = json.dumps(code)
print("\n" + "=" * 60)
print("✅ STRING OUTPUT (met \\n zichtbaar):")
print("=" * 60)
print(escaped)
print("=" * 60)
