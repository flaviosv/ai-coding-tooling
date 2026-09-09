# Disk Evaluate — Playbook

Domain knowledge for `disk-evaluate`: category definitions, read-only verification commands, per-category safe-to-suggest commands, and macOS/Docker/Kubernetes environment gotchas that change machine to machine. Refined from a real cleanup session on 2026-09-03 — the key lesson: **never blanket-prune Docker**, since a dev machine commonly runs a live local Kubernetes cluster and stopped-but-still-needed `docker-compose` stacks that a naive `docker system prune --volumes` would destroy.

## Environment facts to re-check every run

These differ machine to machine and change over time — verify fresh, don't assume a past finding still holds:

- Identify what's actually managing Docker (OrbStack, Docker Desktop, Colima, etc.) — its virtual disk file is often the single largest consumer of disk space on the machine.
- Check for a local Kubernetes cluster running as Docker containers (`k3d`, `kind`, `minikube`'s docker driver, or a built-in VM feature like OrbStack's Kubernetes). If one exists, its workload images are pulled into each node's *internal* containerd store — they can show `CONTAINERS: 0` in `docker images` even while actively deployed as pods. Container count on the host is not a reliable signal of whether an image is in use whenever a nested runtime like this is present.
- Check for a local image registry container (commonly on a `localhost:<port>` mapping) feeding that cluster — it holds its own authoritative copies independent of the host's `docker images` cache.
- Any docker-compose stack currently in a *stopped* (not removed) state is a candidate to still be needed later. Stopped ≠ orphaned — a stack's containers and volumes stay intact unless the project behind it is confirmed dead.

## Verify what's actually live (read-only, always safe to run)

```bash
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'      # running + stopped containers
kubectl config get-contexts                                            # discover any local cluster context(s) present
kubectl --context <local-cluster-context> get pods -A -o wide          # what's actually deployed in that cluster
curl -s http://localhost:<registry-port>/v2/_catalog                   # what a local registry holds, if one is running
docker system df -v                                                    # images/volumes/build-cache breakdown with reclaimable sizes
```

Cross-reference: an image with 0 host containers can still back a running pod (check kubectl) or be a genuinely dead build (check both kubectl and any local registry catalog) — never assume based on host container count alone.

## 1. Docker / local Kubernetes

**Never suggest** `docker system prune` or `docker system prune --volumes` on a machine with a live cluster or stopped compose stacks — it removes **all** stopped containers unconditionally, which then orphans their volumes for the same command's `--volumes` pass.

**Safe to suggest** (each only ever removes items with zero references across running *and* stopped containers):

```bash
docker image prune -a -f     # unused image layers only — protects images used by any existing container
docker volume prune -f       # anonymous/hash-named unused volumes only (Docker 25+ default) — named volumes untouched
docker builder prune -f      # build cache — unrelated to containers/volumes, always safe
```

`docker volume prune -f` behavior has changed across versions: as of Docker 25+, without `-a`/`--all` it only removes **anonymous** volumes, not named-but-unused ones. Confirm the installed version's default with `docker volume prune --help` before assuming.

**Named-but-unused volumes** (from a fully torn-down project, no existing container references them at all) need individual review before suggesting removal — they may hold real data (a database, a workflow store) for a project the user intends to restart later:

```bash
docker system df -v | awk '/Local Volumes space usage/{flag=1} flag' | awk '$2==0'   # list unused volumes with link count
docker volume rm <name>                                                               # suggest one at a time, by name, after review
```

**Orphaned images from renamed/retired projects**: cross-check `docker images` sizes against currently-deployed image names — identical byte sizes across two differently-named repositories is a strong signal one is a stale predecessor of the other (a project rename), safe to suggest removing the old one:

```bash
docker rmi $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -E '^<old-project-name>')
```

## 2. Homebrew

`brew cleanup --dry-run` only reports ~2GB by default (it keeps recent installer downloads for reinstall). The full cache is safe to suggest wiping — everything in it is re-downloadable:

```bash
brew cleanup -s                # conservative default
rm -rf "$(brew --cache)"       # full purge of the download cache
```

## 3. Dev / language package caches

All of the following are re-fetched automatically on next use — safe to suggest:

```bash
uv cache clean
go clean -cache
npm cache clean --force
pip3 cache purge
rm -rf ~/.npm/_npx ~/Library/Caches/node-gyp ~/.cache/codex-runtimes ~/Library/Caches/JetBrains/*
rm -rf ~/.cache/puppeteer                  # re-fetches Chromium on next run
npx playwright uninstall --all             # re-fetches browsers on next run
```

**Not a cache — flag for manual review, never bundle:** `~/.ollama` holds actual downloaded model weights, not reclaimable cache. Suggest `ollama list` then `ollama rm <model>` for ones no longer needed, per-model.

## 4. System / app update caches

Updater/installer leftovers — apps redownload updates as needed, safe to suggest:

```bash
rm -rf ~/Library/Caches/com.spotify.client \
       ~/Library/Caches/electron ~/Library/Caches/electron-builder \
       ~/Library/Caches/com.deezer.deezer-desktop.ShipIt \
       ~/Library/Caches/deezer-desktop-updater \
       ~/Library/Caches/com.postmanlabs.mac.ShipIt \
       ~/Library/Caches/com.tinyspeck.slackmacgap.ShipIt \
       ~/Library/Caches/@granolaelectron-updater \
       ~/Library/Caches/lens-desktop-updater \
       ~/Library/Application\ Support/Google/Chrome/OptGuideOnDeviceModel \
       ~/Library/Application\ Support/Google/GoogleUpdater/crx_cache
```

## 5. Dev artifacts (`node_modules`)

Safe to suggest for any project not actively being worked on right now — `npm install`/`yarn` rebuilds it:

```bash
find ~/Projects -maxdepth 4 -name node_modules -type d -exec du -sh {} \;   # size each one first
rm -rf ~/Projects/<project>/node_modules                                    # suggest removal selectively, never as a batch
```

## 6. Large individual files — manual review only, no blanket command

Never suggest deleting these by pattern — list and flag case by case:

```bash
find ~ -xdev -type f -size +500M -not -path "*/OrbStack/*" -exec du -h {} \; | sort -rh
```

Typical candidates from past runs: personal `.mov`/`.mp4` recordings in `Movies`/`Downloads`, old `.sql.gz` database backups inside project folders, stale installer `.dmg`/`.zip` files already covered by the Homebrew cache purge above.

## Verification commands (for the user to run after they act on a suggestion)

```bash
df -h /System/Volumes/Data                                    # confirm space actually freed
docker system df                                               # confirm docker reclaimable dropped
docker ps -a --format '{{.Names}} {{.Status}}'                 # confirm no containers were lost
kubectl --context <local-cluster-context> get pods -A --no-headers   # confirm no pod crashed or restarted, if a local cluster exists
```
