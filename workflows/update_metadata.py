
# Tento nastroj slouzi k aktualizaci metadat v repozitari MLAB modulu 
# Je potreba ho spoustet z rootu repozitare

from github import Github
import yaml, json
from yaml import load, dump
from yaml import CLoader as Loader, CDumper as Dumper
import os
from glob import glob
from datetime import datetime, timezone

g = Github(os.environ['gh_token'])
repo = g.get_repo(os.environ['gh_repository'])
print(repo)

config_file = 'doc/metadata.yaml'
new = 0

try:
    stream = open(config_file, 'r')
    data = yaml.full_load(stream)
    stream.close()
except:
    print("Soubor neexistuje")
    data = None

stream = open(config_file, 'w+')
print(data, type(data))

if data:
    new = 0
else:
    data = {}
    data['homepage'] = False
    data['mark'] = 50
    data['status'] = 0 
    new = 1

original_data = data.copy()

if new:
    pass

data['description'] = repo.description
data['github_description'] = repo.description
data['github_url'] = os.environ.get('gh_url', "https://www.github.com/MLAB-project")
#data['github_org'] = os.environ.get('gh_org', 'repository_org')
data['github_repo'] = os.environ.get('gh_repo', "repository_name")
data['github_branch'] = os.environ.get('gh_branch', "repository_branch")
data['tags'] = repo.get_topics()
data['title'] = data['github_repo']

## Try to find json file

config_json = data['github_branch']+'.json'

try:
    stream_json = open(config_json, 'r')
    json_data = json.load(stream)
    stream_json.close()
except:
    print("Soubor neexistuje")
    json_data = None

if new and json_data:
    data['status'] = json_data.get('status', 0)
    data['mark'] = json_data.get('mark', 25)

#if not 'images' in data:
images = glob("**/*.jpg", recursive=True)
images.extend(glob("**/*.JPG", recursive=True))
images.extend(glob("**/*.png", recursive=True))
images.extend(glob("**/*.PNG", recursive=True))
images.extend(glob("**/*.gif", recursive=True))
images.extend(glob("**/*.GIF", recursive=True))
images.extend(glob("**/*.svg", recursive=True))
images.extend(glob("**/*.SVG", recursive=True))

data['images'] = []
for x in images:
    if "asset" not in x:
        print("Add", x)
        data['images'].append(x)

# try to guess schematics file
scheme = glob("doc/**/*schematic.pdf", recursive=True)
if len(scheme):
    data['mod_scheme'] = scheme[0]

scheme = glob("hw/**/*ibom.html", recursive=True)
if len(scheme):
    data['mod_ibom'] = scheme[0]


# if not original_data == data:
data['updated'] = datetime.now(timezone.utc).isoformat()

print(data)
yaml.dump(data, stream)
stream.close()
