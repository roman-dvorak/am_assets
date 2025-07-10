## Directory containig GitHub automation worflow.

 - `kicad_outputs.yml` - KiCAD manufacturing and documentation outputs automation.

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
