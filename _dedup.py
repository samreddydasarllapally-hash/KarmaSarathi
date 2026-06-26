import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app/agents/planner.py', encoding='utf-8') as f:
    content = f.read()

# Remove the first (duplicate) _confirm_response definition
# They are identical — find the first occurrence and remove it
marker = 'def _confirm_response(s) -> str:'
first  = content.find(marker)
second = content.find(marker, first + 1)

if second != -1:
    # Remove from first up to (but not including) second occurrence
    content = content[:first] + content[second:]
    print("Duplicate removed. Occurrences remaining:", content.count(marker))
else:
    print("No duplicate found. Occurrences:", content.count(marker))

with open('app/agents/planner.py', 'w', encoding='utf-8') as f:
    f.write(content)
