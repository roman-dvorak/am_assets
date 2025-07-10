
# This tool should update kitspace.yaml metadata file.
# It should be run from the repository root.

from github import Github
import yaml
from yaml import load, dump
from yaml import CLoader as Loader, CDumper as Dumper
import os
from glob import glob

g = Github(os.environ['gh_token'])
repo = g.get_repo(os.environ['gh_repository'])
print(repo)

config_file = 'kitspace.yaml'
new = 0

try:
    stream = open(config_file, 'r')
    data = yaml.full_load(stream)
    stream.close()
except:
    print("File does not exists")
    data = None

stream = open(config_file, 'w+')
print(data, type(data))

if data:
    new = 0
else:
    data = {}
    new = 1

if new:
    pass

data['summary'] = repo.description
data['site'] = os.environ.get('gh_url', "https://www.github.com/MLAB-project")
data['color'] = 'white'
data['bom'] = 'hw/sch_pcb/'+os.environ.get('gh_repo', "repository_name")+'.kicad_pcb'
data['gerbers'] = 'hw/cam_profi/'
data['eda'] = {}
data['eda']['type'] = 'kicad'
data['eda']['pcb'] = 'hw/sch_pcb/'+os.environ.get('gh_repo', "repository_name")+'.kicad_pcb'
    
print(data)
yaml.dump(data, stream)
stream.close()
