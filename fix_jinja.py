import os
import re

template_dir = 'c:\\Users\\ganes\\Downloads\\IPL_Auction\\templates'

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # TEAM_THEME[var].primary -> TEAM_THEME.get(var, {}).get('primary', '#1D4ED8')
    content = re.sub(
        r'TEAM_THEME\[([\w\.]+)\]\.primary',
        r"TEAM_THEME.get(\1, {}).get('primary', '#1D4ED8')",
        content
    )

    # TEAM_THEME[var].short -> TEAM_THEME.get(var, {}).get('short', \1)
    content = re.sub(
        r'TEAM_THEME\[([\w\.]+)\]\.short',
        r"TEAM_THEME.get(\1, {}).get('short', \1)",
        content
    )

    # TEAM_LOGOS[var] -> TEAM_LOGOS.get(var, 'images/teams/mi.png')
    content = re.sub(
        r'TEAM_LOGOS\[([\w\.]+)\]',
        r"TEAM_LOGOS.get(\1, 'images/teams/mi.png')",
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filename in os.listdir(template_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(template_dir, filename)
        process_file(filepath)

print("Jinja templates hardened.")
