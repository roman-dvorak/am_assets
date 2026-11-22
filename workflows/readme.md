## Directory containig GitHub automation worflow.

 - `kicad_outputs.yml` - KiCAD manufacturing and documentation outputs automation. Matrix over the PCB designs
   of the repository; every PCB runs the reusable workflow `kicad_pcb.yml` with the individual output jobs
   (ERC, DRC, schematics, placement, report, iBOM, 3D, gerbers, CAD and render).
   - push to a branch: the outputs are committed to the repository (`doc/gen/`, `hw/cam_profi/`);
   - published release (tag `<revision>-release`) or manual run with a tag: the tagged commit is built and
     per PCB `<rev>-<sha>-gerbers.zip` (manufacturing), `<rev>-<sha>-assembly.zip` (iBOM, netlists, positions, JLCPCB BOM + CPL)
     and `<rev>-<sha>-intranet.zip` (metadata.json, netlists, iBOM, BOM CSV, schematic PDF, PNG previews)
     are attached to the release.
 - `kicad_pcb.yml` - reusable workflow (`workflow_call`) with the outputs of one PCB, called by `kicad_outputs.yml`.
 - `release_metadata.py` - writes metadata.json of the intranet package (board size, layers, title block,
   component list from the netlist, file list with SHA-256, commit and release info).
 - `pcb_matrix.py` - finds the PCB designs and prints the matrix (`python3 doc/assets/workflows/pcb_matrix.py`).
 - `update_actions.yml` - daily update of the assets submodule and of the workflow files.

### More PCB designs in one repository

The PCBs are found in this order:

 1. `hw/sch_pcb/PCB_matrix.yaml` (same format as USTassets):
    ```yaml
    - name: AMRAIN01-SENS               # project name = stem of .kicad_pro/.kicad_sch/.kicad_pcb
      dir: hw/sch_pcb/AMRAIN01-SENS     # optional, default hw/sch_pcb/<name>
    - name: AMRAIN01-INTERFACE
      extra_layers: [Cmts.User]         # optional, extra gerber layers
    ```
 2. `hw/sch_pcb/<project>.kicad_pcb` - single board (project = repository name without `-internal`).
 3. every `hw/sch_pcb/*.kicad_pcb` and `hw/sch_pcb/<x>/<x>.kicad_pcb`.

A single board in `hw/sch_pcb/` keeps the flat output layout (`doc/gen/`, `hw/cam_profi/`), more boards get
a subdirectory each (`doc/gen/<name>/`, `hw/cam_profi/<name>/`). Output files are renamed from the project
name to the revision (branch): the project prefix of the board name is replaced, e.g. `AMRAIN01-SENS` on
branch `AMRAIN01A` -> `AMRAIN01A-SENS`.

  In case of creation of a new module from [module template](https://github.com/mlab-modules/MODUL01/tree/MODUL01A/.github/workflows) use `copy_workflow_to_repo.sh` script to copy the workflow file to the new MLAB module repository.  


## Update assets submodule in single command (

That is useful for example for older MLAB modules originally established with older KiCAD versions

```
git pull; git submodule update --init --remote; cd doc/assets/workflows; ./copy_workflow_to_repo.sh; cd ../../..; git add .gitmodules doc/assets/ .github; git commit -m"update actions"; git push 
```


.gitmodules
```
[submodule "doc/assets"]
        path = doc/assets
        url = git@github.com:MLAB-project/documents.git
        branch = old_mlab_naming
        shallow = true
```
