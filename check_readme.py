"""Temp: verify README Day headings. Deleted after use."""

with open("README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

headings = [line.rstrip("\n") for line in lines if line.startswith("## Day ")]
day30 = [h for h in headings if h.startswith("## Day 30")]
assert len(headings) == 23, f"expected 23 Day headings, got {len(headings)}"
assert len(day30) == 1, f"expected exactly 1 Day 30 heading, got {len(day30)}"
assert headings[-1] == "## Day 30 - Prompt Readiness Report Export", headings[-1]
assert headings[-2] == "## Day 29 - Prompt Readiness Report", headings[-2]

content = "".join(lines)
assert "## Day 31" not in content
print(f"OK: {len(headings)} Day headings, last = {headings[-1]}")
