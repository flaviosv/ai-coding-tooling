#!/usr/bin/env bash
# Read-only. Lists images cached inside each k3d node that are safe to remove:
# local-registry builds (e.g. old Tilt tags) that no container on the node uses
# (any state) and no workload spec references (including ones scaled to 0).
# Public/system images (pause, coredns, traefik, ...) are never listed.
#
# Usage: k3d_stale_images.sh <k3d-cluster-name> [registry-url]
#   e.g. k3d_stale_images.sh local http://localhost:5001
# Output (stdout, TSV): node  image-id  size-MB  tags
# Summary and warnings go to stderr.
set -euo pipefail

cluster="${1:?usage: k3d_stale_images.sh <k3d-cluster-name> [registry-url]}"
registry_url="${2:-}"
context="k3d-${cluster}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

registry_name="$(docker ps --filter "label=k3d.cluster=${cluster}" --filter "label=k3d.role=registry" --format '{{.Names}}' | head -1)"
[ -n "$registry_name" ] || { echo "no k3d registry container for cluster '${cluster}'" >&2; exit 1; }
prefix="${registry_name}:5000/"

kubectl --context "$context" get deploy,sts,ds,job,cronjob,pod -A -o json \
  | jq -r '.. | objects | select(has("image") and (.image|type=="string")) | .image' \
  | sed 's#^docker.io/##' | sort -u > "$tmp/referenced"

if [ -n "$registry_url" ]; then
  grep "^${prefix}" "$tmp/referenced" | while read -r ref; do
    repo="${ref#"$prefix"}"; tag="${repo##*:}"; repo="${repo%:*}"
    code="$(curl -s -o /dev/null -w '%{http_code}' \
      -H 'Accept: application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json' \
      "${registry_url}/v2/${repo}/manifests/${tag}")"
    [ "$code" = 200 ] || echo "WARN: referenced ${repo}:${tag} not in registry (HTTP ${code}) — a restart could not re-pull it" >&2
  done
fi

total=0
for node in $(docker ps --filter "label=k3d.cluster=${cluster}" --format '{{.Names}} {{.Label "k3d.role"}}' | awk '$2=="server" || $2=="agent" {print $1}' | sort); do
  docker exec "$node" crictl ps -a -o json | jq -r '.containers[].imageRef' | sort -u > "$tmp/used"
  docker exec "$node" crictl images -o json | jq -r \
    --rawfile used "$tmp/used" --rawfile ref "$tmp/referenced" --arg prefix "$prefix" --arg node "$node" '
      ($used | split("\n")) as $u | ($ref | split("\n")) as $r
      | .images[]
      | select(.pinned | not)
      | select((.id as $i | $u | index($i)) | not)
      | select((.repoTags | length) > 0 and all(.repoTags[]; startswith($prefix)))
      | select(any(.repoTags[]; . as $t | $r | index($t)) | not)
      | "\($node)\t\(.id)\t\(.size | tonumber / 1e6 | floor)\t\(.repoTags | join(","))"' > "$tmp/stale"
  cat "$tmp/stale"
  node_mb="$(awk -F'\t' '{s+=$3} END{print s+0}' "$tmp/stale")"
  echo "${node}: $(wc -l < "$tmp/stale" | tr -d ' ') stale images, ~${node_mb} MB" >&2
  total=$((total + node_mb))
done
echo "total: ~${total} MB (compressed image size; unpacked snapshots freed on top)" >&2
