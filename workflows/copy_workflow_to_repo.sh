
#  zkopiruje workflow soubor do nadrazeneho repozitare
#  Predpoklada se, ze tento repozitar je jako submodul
#  a je umisten v `/doc/assets`
#

mkdir -p ../../../.github/workflows

if [ "$(find ../../../hw -name '*kicad_pro'  2>/dev/null)" ]
then
	echo "This is KICAD project"
	cp kicad_outputs.yml ../../../.github/workflows/kicad_outputs.yml
	cp kicad_pcb.yml ../../../.github/workflows/kicad_pcb.yml
else
   rm ../../../.github/workflows/kicad_outputs.yml ../../../.github/workflows/kicad_pcb.yml 2>/dev/null || true
   echo "Kicad not found"
fi
cp update_actions.yml ../../../.github/workflows/update_actions.yml
# the release packages are built by kicad_outputs.yml (release event), the metadata updater is not used any more
rm -f ../../../.github/workflows/release_assets.yml ../../../.github/workflows/metadata_updater.yml


cp gitattribudes ../../../.gitattributes
# merge the template into the repository .gitignore (through a temporary file: redirecting straight
# into .gitignore would truncate it before it is read and drop the repository's own rules)
tmp=$(mktemp)
cat gitignore ../../../.gitignore 2>/dev/null | sort | uniq > "$tmp"
mv "$tmp" ../../../.gitignore
