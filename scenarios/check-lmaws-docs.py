#!/usr/bin/env python3
"""Offline catalogue checks: lifecycle entry points and runnable image captions."""
from pathlib import Path
import re
root=Path(__file__).resolve().parent
for number in ['01','02','03','04','05','06','11']:
    folder=next(root.glob(number+'-*'))/'lmaws'
    for name in ['up','test','down','status','all']:
        text=(folder/(name+'.lms')).read_text()
        assert text.lstrip().startswith('# === CONFIG'),(number,name,'CONFIG must come first')
    readme=(folder/'README.md').read_text()
    assert readme.lstrip().startswith('!['),(number,'pictures first')
    for match in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)',readme):
        assert (folder/match.group(1)).is_file(),match.group(1)
        caption=readme[match.end():].split('![',1)[0]
        assert re.search(r'lmctl\s+[^`\n]*\.lms',caption),(number,'image needs a runnable caption')
    assert 'see source' not in readme.lower()
print('PASS seven lmaws layouts, CONFIG sections, local image links and runnable captions')
