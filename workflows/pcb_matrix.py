#!/usr/bin/env python3
"""Find the KiCad PCB designs of a repository and print the GitHub Actions matrix.

Run from the repository root (the parent of doc/assets).

Sources, first match wins:
  1. hw/sch_pcb/PCB_matrix.yaml - explicit list (same format as USTassets):
        - name: AMRAIN01-SENS                 # project name (= .kicad_pro/.kicad_sch/.kicad_pcb stem)
          dir: hw/sch_pcb/AMRAIN01-SENS       # optional, default hw/sch_pcb/<name>
          extra_layers: [Cmts.User]           # optional, extra gerber layers
  2. hw/sch_pcb/<project>.kicad_pcb - single board, legacy layout (project = repo name without "-internal")
  3. every hw/sch_pcb/*.kicad_pcb and hw/sch_pcb/<dir>/<dir>.kicad_pcb

Every matrix entry has
  name          project name
  dir           directory with the project
  schema/board  paths to .kicad_sch/.kicad_pcb
  extra_layers  list of extra gerber layers
  out           file name prefix of the outputs: <project> prefix of the name replaced by <revision>
                (e.g. AMRAIN01-SENS on branch AMRAIN01A -> AMRAIN01A-SENS; single board -> AMRAIN01A)
  sub           output subdirectory: "" for a single board (legacy flat layout), "<name>/" otherwise

Usage:
  pcb_matrix.py [--revision REV] [--github]   print the matrix JSON (--github: also write matrix=, project=, count= to $GITHUB_OUTPUT)
  pcb_matrix.py --names                       print one project name per line
"""
import argparse
import glob
import json
import os
import sys

MATRIX_FILE = 'hw/sch_pcb/PCB_matrix.yaml'


def project_name():
    repo = os.environ.get('GITHUB_REPOSITORY', '').split('/')[-1] or os.path.basename(os.getcwd())
    return repo[:-len('-internal')] if repo.endswith('-internal') else repo


def entry(name, d, extra_layers=None):
    return {
        'name': name,
        'dir': d,
        'schema': f'{d}/{name}.kicad_sch',
        'board': f'{d}/{name}.kicad_pcb',
        'extra_layers': list(extra_layers or []),
    }


def discover(project):
    if os.path.isfile(MATRIX_FILE):
        import yaml
        with open(MATRIX_FILE) as f:
            items = yaml.safe_load(f) or []
        return [entry(p['name'], (p.get('dir') or f'hw/sch_pcb/{p["name"]}').rstrip('/'), p.get('extra_layers'))
                for p in items]
    if os.path.isfile(f'hw/sch_pcb/{project}.kicad_pcb'):
        return [entry(project, 'hw/sch_pcb')]
    found = sorted(glob.glob('hw/sch_pcb/*.kicad_pcb'))
    found += sorted(p for p in glob.glob('hw/sch_pcb/*/*.kicad_pcb')
                    if os.path.basename(os.path.dirname(p)) == os.path.basename(p)[:-len('.kicad_pcb')])
    return [entry(os.path.basename(p)[:-len('.kicad_pcb')], os.path.dirname(p)) for p in found]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--revision', default=os.environ.get('GITHUB_HEAD_REF') or os.environ.get('GITHUB_REF_NAME') or '',
                    help='revision (branch, release tag without "-release") used in the output names')
    ap.add_argument('--project', default=project_name())
    ap.add_argument('--github', action='store_true')
    ap.add_argument('--names', action='store_true')
    args = ap.parse_args()

    pcbs = discover(args.project)
    if not pcbs:
        sys.exit('No KiCad board found (hw/sch_pcb/PCB_matrix.yaml, hw/sch_pcb/*.kicad_pcb, hw/sch_pcb/<x>/<x>.kicad_pcb)')
    single = len(pcbs) == 1 and pcbs[0]['dir'] == 'hw/sch_pcb'
    rev = args.revision or args.project
    for p in pcbs:
        p['out'] = rev + p['name'][len(args.project):] if p['name'].startswith(args.project) else p['name']
        p['sub'] = '' if single else p['name'] + '/'

    if args.names:
        print('\n'.join(p['name'] for p in pcbs))
        return
    matrix = json.dumps({'include': pcbs})
    print(matrix)
    if args.github and os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'matrix={matrix}\nproject={args.project}\ncount={len(pcbs)}\n')


if __name__ == '__main__':
    main()
