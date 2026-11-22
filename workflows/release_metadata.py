#!/usr/bin/env python3
"""Write metadata.json of one PCB for the intranet release package.

Reads the board (.kicad_pcb, plain S-expression parsing, no KiCad needed) and the KiCad netlist (.net,
KiBot `netlist` output, format classic) and writes a JSON description of the release:
project, revision, commit, board size/layers/thickness, title block, component list, list of the files
in the package with size and SHA-256, and the names of the other release assets.

Usage (from the repository root):
  release_metadata.py --name AMMCUBOARD01 --revision AMMCUBOARD01A --tag AMMCUBOARD01A-release \
      --board hw/sch_pcb/AMMCUBOARD01.kicad_pcb --netlist out/AMMCUBOARD01-netlist.net \
      --package pkg/AMMCUBOARD01A-abc1234-intranet --asset AMMCUBOARD01A-abc1234-gerbers.zip ... \
      -o pkg/AMMCUBOARD01A-abc1234-intranet/metadata.json
"""
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import subprocess

SCHEMA_VERSION = 1


def git(*args):
    try:
        return subprocess.check_output(['git', *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def sexpr_blocks(text, head):
    """Yield the full text of every balanced '(head ...)' block."""
    for m in re.finditer(r'\(' + re.escape(head) + r'[\s)]', text):
        depth, i, instr = 0, m.start(), False
        while i < len(text):
            c = text[i]
            if instr:
                if c == '\\':
                    i += 1
                elif c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    yield text[m.start():i + 1]
                    break
            i += 1


def unquote(s):
    return s.replace('\\"', '"').replace('\\\\', '\\')


def board_info(path):
    text = open(path, encoding='utf-8').read()
    info = {'file': path}

    m = re.search(r'\(general\s*\(thickness\s+([\d.]+)', text)
    info['thickness_mm'] = float(m.group(1)) if m else None

    layers = next(sexpr_blocks(text, 'layers'), '')
    info['copper_layers'] = len(re.findall(r'\(\d+\s+"[^"]*\.Cu"', layers))

    # board outline: Edge.Cuts graphics of the board (not inside footprints)
    body = text
    for fp in sexpr_blocks(text, 'footprint'):
        body = body.replace(fp, '')
    xs, ys = [], []
    for kind in ('gr_line', 'gr_arc', 'gr_rect', 'gr_circle', 'gr_poly', 'gr_curve'):
        for blk in sexpr_blocks(body, kind):
            if '"Edge.Cuts"' not in blk:
                continue
            pts = [(float(a), float(b)) for a, b in
                   re.findall(r'\((?:start|end|mid|center|xy)\s+(-?[\d.]+)\s+(-?[\d.]+)', blk)]
            if kind == 'gr_circle' and len(pts) >= 2:
                (cx, cy), (ex, ey) = pts[0], pts[1]
                r = math.hypot(ex - cx, ey - cy)
                pts = [(cx - r, cy - r), (cx + r, cy + r)]
            for x, y in pts:
                xs.append(x)
                ys.append(y)
    if xs:
        info['size_mm'] = {'width': round(max(xs) - min(xs), 3), 'height': round(max(ys) - min(ys), 3)}
        info['outline_bbox_mm'] = [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]
    else:
        info['size_mm'] = None

    tb = next(sexpr_blocks(text, 'title_block'), '')
    title = {}
    for key in ('title', 'date', 'rev', 'company'):
        m = re.search(r'\(' + key + r'\s+"((?:[^"\\]|\\.)*)"', tb)
        if m and m.group(1):
            title[key] = unquote(m.group(1))
    comments = {n: unquote(v) for n, v in re.findall(r'\(comment\s+(\d+)\s+"((?:[^"\\]|\\.)*)"', tb) if v}
    if comments:
        title['comments'] = comments
    info['title_block'] = title
    return info


def netlist_info(path):
    text = open(path, encoding='utf-8').read()
    comps = []
    for blk in sexpr_blocks(text, 'comp'):
        def val(key):
            m = re.search(r'\(' + key + r'\s+"((?:[^"\\]|\\.)*)"', blk)
            return unquote(m.group(1)) if m else None
        ref = val('ref')
        if not ref or ref.startswith('#'):
            continue
        fields = {unquote(n): unquote(v) for n, v in
                  re.findall(r'\(field\s+\(name\s+"((?:[^"\\]|\\.)*)"\)\s*"((?:[^"\\]|\\.)*)"', blk) if v}
        props = {unquote(n) for n in re.findall(r'\(property\s*\(name\s+"((?:[^"\\]|\\.)*)"', blk)}
        lib = re.search(r'\(libsource\s+\(lib\s+"([^"]*)"\)\s*\(part\s+"([^"]*)"', blk)
        sheet = re.search(r'\(sheetpath\s+\(names\s+"([^"]*)"', blk)
        comps.append({
            'ref': ref,
            'value': val('value'),
            'footprint': val('footprint'),
            'symbol': f'{lib.group(1)}:{lib.group(2)}' if lib else None,
            'datasheet': val('datasheet') if val('datasheet') not in (None, '~', '') else None,
            'description': val('description'),
            'fields': fields,
            'dnp': 'dnp' in props,
            'exclude_from_bom': 'exclude_from_bom' in props,
            'sheet': sheet.group(1) if sheet else None,
        })
    nets = len(re.findall(r'\(net\s*\(code\s', text))
    key = lambda c: (re.sub(r'\d+', '', c['ref']), int(re.sub(r'\D', '', c['ref']) or 0), c['ref'])
    comps.sort(key=key)
    return {
        'file': os.path.basename(path),
        'nets': nets,
        'components_total': len(comps),
        'components_fitted': sum(1 for c in comps if not c['dnp']),
        'components_dnp': sum(1 for c in comps if c['dnp']),
        'components': comps,
    }


def file_list(directory, skip):
    out = []
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            p = os.path.join(root, f)
            rel = os.path.relpath(p, directory)
            if rel == skip:
                continue
            h = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            out.append({'path': rel, 'size': os.path.getsize(p), 'sha256': h})
    return sorted(out, key=lambda x: x['path'])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--name', required=True, help='project name (stem of the KiCad files)')
    ap.add_argument('--revision', required=True, help='hardware revision, e.g. AMMCUBOARD01A')
    ap.add_argument('--out-name', help='output name prefix (matrix "out"), default = revision')
    ap.add_argument('--tag', default='')
    ap.add_argument('--board', required=True)
    ap.add_argument('--schema')
    ap.add_argument('--netlist')
    ap.add_argument('--package', help='package directory, its files are listed with SHA-256')
    ap.add_argument('--asset', action='append', default=[], help='other release asset (repeatable)')
    ap.add_argument('-o', '--output', required=True)
    args = ap.parse_args()

    server = os.environ.get('GITHUB_SERVER_URL', 'https://github.com')
    repo = os.environ.get('GITHUB_REPOSITORY')
    run_id = os.environ.get('GITHUB_RUN_ID')
    meta = {
        'schema_version': SCHEMA_VERSION,
        'project': args.name,
        'revision': args.revision,
        'name': args.out_name or args.revision,
        'release': {
            'tag': args.tag or None,
            'url': f'{server}/{repo}/releases/tag/{args.tag}' if repo and args.tag else None,
            'assets': args.asset,
        },
        'source': {
            'repository': f'{server}/{repo}' if repo else None,
            'commit': git('rev-parse', 'HEAD'),
            'commit_short': git('rev-parse', '--short', 'HEAD'),
            'commit_date': git('show', '-s', '--format=%cI', 'HEAD'),
            'board_file': args.board,
            'schematic_file': args.schema,
        },
        'build': {
            'date': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'workflow_run': f'{server}/{repo}/actions/runs/{run_id}' if repo and run_id else None,
            'assets_commit': git('-C', 'doc/assets', 'rev-parse', 'HEAD'),
        },
        'board': board_info(args.board),
    }
    if args.netlist:
        meta['bom'] = netlist_info(args.netlist)
    if args.package:
        meta['files'] = file_list(args.package, os.path.relpath(os.path.abspath(args.output),
                                                                 os.path.abspath(args.package)))
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print(f'{args.output}: {meta["board"].get("size_mm")} mm, {meta["board"]["copper_layers"]} Cu, '
          f'{meta.get("bom", {}).get("components_total", "?")} components')


if __name__ == '__main__':
    main()
