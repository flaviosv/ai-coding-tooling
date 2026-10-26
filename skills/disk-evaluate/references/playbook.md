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

### Stale builds cached inside k3d nodes (old Tilt tags)

Each k3d node keeps its own containerd image store, and every Tilt rebuild leaves the previous tag behind in it — on a long-lived dev cluster this is commonly the largest reclaimable item on the machine (tens of GB), invisible to `docker system df`. Find them with the bundled read-only script:

```bash
scripts/k3d_stale_images.sh <k3d-cluster-name> http://localhost:<registry-port>   # TSV per image + per-node summary on stderr
```

It lists only images whose every tag comes from the cluster's local registry, that no container on that node uses (any state), and that no Deployment/StatefulSet/DaemonSet/Job/CronJob/Pod spec references — workloads scaled to 0 included. A `WARN` line means a currently-referenced tag is missing from the registry; resolve that before suggesting removal. Removing these never touches the registry, so every build stays pullable. Suggest removal by exact image ID, per node:

```bash
docker exec <node> crictl rmi <image-id> ...
```

**Never suggest `crictl rmi --prune`** inside a k3d node: on k3s the pause image (`rancher/mirrored-pause`) is not pinned and has no container referencing it, so a blanket prune deletes it along with system images (coredns, traefik, metrics-server) and the images of scaled-to-0 workloads.

**Local registry content** (repos/tags no workload references) is a separate, manual-only item: the k3d registry has deletes disabled, so freeing it means removing repository directories and running `registry garbage-collect` while nothing is pushing — report the unreferenced repos, never a size estimate (layers are shared across repos).

## 2. Homebrew

`brew cleanup --dry-run` only reports ~2GB by default (it keeps recent installer downloads for reinstall). The full cache is safe to suggest wiping — everything in it is re-downloadable:

```bash
brew cleanup -s                # conservative default
brew --cache                   # resolve the path first (typically ~/Library/Caches/Homebrew), then remove it by literal path
rm -rf ~/Library/Caches/Homebrew
```

Suggest `rm -rf` targets as literal paths: Claude Code's safety check blocks `rm -rf "$(...)"` because the target can't be verified before it runs.

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

## 5. Dev artifacts (`node_modules`, `.venv`, build output)

Safe to suggest for any project not actively being worked on right now — `npm install`/`yarn`/`uv sync`/`composer install` rebuilds it:

```bash
find ~/Projects -maxdepth 5 \( -name node_modules -o -name .venv -o -name vendor -o -name dist -o -name build -o -name .terraform -o -name Pods \) -type d -prune -exec du -sk {} + | sort -rn | head -40   # size each one first
rm -rf ~/Projects/<project>/node_modules                                    # suggest removal selectively, never as a batch
```

### Measuring `~/Projects` without reading project contents

When the user says projects are private or must not be read, measure sizes and names only — never open files, grep, or run `git log`/`git diff` inside them:

```bash
cd ~/Projects && du -sh -- */ | sort -rh                      # per-project totals
du -h -d 2 . | sort -rh | head -40                            # where the weight sits, two levels down
find . -maxdepth 5 -name .git -type d -prune -exec du -sk {} + | sort -rn | head -10   # oversized histories
find ~/Projects -xdev -type f -size +200M -exec du -h {} + | sort -rh                  # large single files
```

Identical `.git/objects/pack/pack-<hash>.pack` file names across different folders mean the same repository was cloned or copied more than once — report them as duplicates, not as separate histories. Test-output folders (`test-runs`, `.plugin-smoke`, `e2e-*`) can hold tens of GB; if their newest entries are minutes old, a producer is still writing — flag as active and suggest keeping the newest few.

## 6. Large individual files — manual review only, no blanket command

Never suggest deleting these by pattern — list and flag case by case:

```bash
find ~ -xdev -type f -size +500M -not -path "*/OrbStack/*" -exec du -h {} \; | sort -rh
```

Typical candidates from past runs: personal `.mov`/`.mp4` recordings in `Movies`/`Downloads`, old `.sql.gz` database backups inside project folders, stale installer `.dmg`/`.zip` files already covered by the Homebrew cache purge above.

## 7. User temp directory (`$TMPDIR`) — leaked test fixtures

`du ~` and `find ~` never see it, yet on 2026-10-24 `/private/var/folders/<xx>/<yyyy>/T` held 172GB: 144,514 entries left by a test harness that created `mkdtemp` directories (`step-tree-*`, throwaway git repos of ~17MB; `step-work-*`, scratch dirs of ~8MB) and never removed them. Check it on every run; a plain `du` over it can take over 5 minutes, so run it in the background with a long timeout.

```bash
getconf DARWIN_USER_TEMP_DIR                                   # resolve the temp dir, then use it as a literal path below
du -sh /private/var/folders 2>/dev/null                        # background it; slow when entries number in the 100k+
ls -A "$T" | wc -l                                             # entry count, fast
ls -A "$T" | sed -E 's/[0-9a-zA-Z]{6,}/X/g; s/[0-9]+/N/g' | sort | uniq -c | sort -rn | head -15   # group by name pattern
find "$T" -maxdepth 1 -name '<pattern>' | wc -l                # count per pattern
find "$T" -maxdepth 1 -name '<pattern>' | head -25 | xargs -I{} du -sk {}                           # sample sizes; estimate = average × count
find "$T" -maxdepth 1 -name '<pattern>' -exec stat -f '%Sm' -t '%Y-%m-%d' {} + | sort | uniq -c    # creation-day histogram
ps -axo pid,etime,command | grep -E '<pattern>|<project-path>' | grep -v grep                       # is a producer running right now
```

In zsh an unquoted glob held in a loop variable does not expand and silently counts 0 — use `find -name`. Do not walk the whole directory with `du -d`/`find -exec du`; sample instead.

To tie fixtures to a producer without reading the project: compare the name stems with the project's run/folder names, the creation-day histogram with the project's worktree dates (`stat -f '%SB'`), and the running processes whose arguments point into the project. Report it as a correlation and name the root-cause fix (the producer must clean up its own temp dirs). Fixtures are disposable, but re-check `ps` immediately before suggesting removal, filter by age so a live run's fixtures are skipped, and suggest it by literal path — expect ~2–3GB/min with millions of small files, so run it in the background:

```bash
find <literal-temp-dir> -maxdepth 1 -mindepth 1 \( -name 'step-tree-*' -o -name 'step-work-*' \) -mmin +60 -exec rm -rf {} +
```

`~/.Trash` and `~/Library/Group Containers/*OrbStack*` return "Operation not permitted" without Full Disk Access — list them as unmeasurable in the report, not as empty.

## 8. Agent worktrees inside projects

Agent and review tooling leaves git worktrees under `<project>/.claude/worktrees` and `<project>/.worktrees` (10GB and 4.3GB in the 2026-10-24 run). Size them with `du -h -d 1`, list the registered ones with `git -C <project> worktree list`, and suggest removal through git so metadata stays consistent:

```bash
git -C <project> worktree remove <path>   # no --force: refuses worktrees with modified or untracked files, which must be reported for the user to decide
git -C <project> worktree prune
```

Removing a worktree does not delete its branch, so committed work survives; `--force` discards uncommitted work and needs the user's explicit say-so per worktree. A `prunable` entry in `worktree list` points at a path that no longer exists and is safe to prune. A `claude --plugin-dir` or editor process pointing into a worktree means it is in use.

## 9. Other places that grow quietly

Rank these with `du -sh ~/Library/Caches/* ~/Library/Application\ Support/* ~/.cache/* 2>/dev/null | sort -rh | head -20` rather than relying on the fixed lists above.

- `~/Library/Application Support/<IDE>` keeps one directory per installed version (`GoLand2026.1`, `GoLand2026.2`, …) — older versions are candidates, but they hold settings, so flag them rather than bundling.
- `~/Library/Application Support/Claude/vm_bundles/**/rootfs.img` (~10GB) is the Claude desktop VM disk — not a cache, flag only.
- `~/Library/Caches/Google/Chrome` (7.6GB) is a browser cache — quit Chrome before suggesting removal.
- `~/.gradle/caches`, `~/go/pkg/mod` (`go clean -modcache`), `~/Library/Caches/{Cypress,goimports,ms-playwright}` and `~/.cache/codex-runtimes` are re-fetched on next use.

## Verification commands (for the user to run after they act on a suggestion)

```bash
df -h /System/Volumes/Data                                    # confirm space actually freed
docker system df                                               # confirm docker reclaimable dropped
docker ps -a --format '{{.Names}} {{.Status}}'                 # confirm no containers were lost
kubectl --context <local-cluster-context> get pods -A --no-headers   # confirm no pod crashed or restarted, if a local cluster exists
```
