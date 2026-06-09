import re, sys
p = sys.argv[1]
s = open(p).read()
s = re.sub(r',([A-Za-z])', r', \1', s)
s = s.replace('in his earlier chapter on the four limits of the testimony',
              'in his chapter on the four limits of the testimony')
open(p, 'w').write(s)
print('ok')
