#!/usr/bin/env bash
# Staged VPS sync — REVIEW then run with:  ! bash docs/workspace/.../run/sync-all.sh
# Pushes standardized <slug>-audit-data.json into the LIVE PRISM grounding store.
# The loop APPENDS verified slugs to SLUGS below; prod write stays human-gated (you run this).
set -euo pipefail

KEY=/Users/arijitchowdhury/.ssh/chowmes_ed25519
H=chowmesadmin@72.61.72.147
HUB=~/prism-hub
STORE=/root/.hermes-prism/reports

# Slugs verified by the loop (passed schema gate). Edit/extend as needed.
SLUGS=(petsmart british-airways labanquepostale brooks-running nike savage-x-fenty oriental-trading llbean dsw homedepot-mexico)

TS=$(date +%Y%m%d-%H%M%S)
echo "=== 1) BACKUP live store → reports.bak-$TS.tar.gz ==="
ssh -i "$KEY" "$H" "sudo tar czf $STORE/../reports.bak-$TS.tar.gz -C $STORE/.. reports && sudo ls -lh $STORE/../reports.bak-$TS.tar.gz | awk '{print \$5, \$9}'"

for slug in "${SLUGS[@]}"; do
  SRC="$HUB/${slug}-audit-data.json"
  [ -f "$SRC" ] || { echo "!! MISSING $SRC — skip $slug"; continue; }
  echo "=== 2) $slug: local md5 $(md5 -q "$SRC") ==="
  scp -i "$KEY" "$SRC" "$H:/tmp/${slug}-audit-data.json"
  ssh -i "$KEY" "$H" "
    sudo mkdir -p $STORE/$slug
    sudo cp /tmp/${slug}-audit-data.json $STORE/$slug/audit-data.json
    echo -n '   VPS md5 after push: '; sudo md5sum $STORE/$slug/audit-data.json | awk '{print \$1}'
    rm -f /tmp/${slug}-audit-data.json
  "
done

echo "=== 3) verify index.json catalogue ==="
ssh -i "$KEY" "$H" "sudo grep -o '\"slug\":[^,]*' $STORE/index.json | head -20 || sudo cat $STORE/index.json | head"
echo "=== DONE. Chat grounds on the new data live (no restart). ==="
