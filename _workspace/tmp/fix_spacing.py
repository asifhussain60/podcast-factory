import re
import sys

paths = [
    '/Users/asifhussain/PROJECTS/podcast-factory/content/drafts/the-master-and-the-disciple/chapters/ch05-father-revealed-and-the-faces-of-seeking.txt',
]

for path in paths:
    with open(path) as f:
        s = f.read()
    # Add a space after commas where the next char is a letter or *.
    # Skip cases like ", " or ",\n" which are already correct.
    s2 = re.sub(r',(?=[A-Za-z*])', ', ', s)
    with open(path, 'w') as f:
        f.write(s2)
    sys.stdout.write(f"{path}\n")
