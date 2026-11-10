# 🧪 CI

A private build runner. No source, no releases, no build files — just workflows that borrow GitHub's servers, build private projects, and send the results back to a private place.

## Why

Private repos get limited free Actions minutes; public ones don't. So the builds run here, and everything they produce goes back to private.

## How it works

1. A workflow starts.
2. It pulls the private source using a token.
3. It builds.
4. `release.py` patches the version, publishes the release, posts to Telegram, and triggers cleanup.
5. A cleanup workflow wipes the run from this repo.

Finished runs get deleted, so the Actions tab stays empty on purpose.

## Workflows

| Workflow | Purpose |
| --- | --- |
| **Unified CI** | Builds any module from any repo/branch using a `pack.txt` manifest. |
| **Cleanup** | Purges old runs and releases. |
| **Toolkit** | Compiles static aarch64 binaries (bash, jq, zip, inotify, abx). |
| **Overlayfsx** | Rust build for the overlayfsx module. |
| **Pages** | Deploys to Cloudflare Pages. |

## Unified CI

One workflow replaces the old per-module builders (appsniper, ashlooper, fontcraft, isolator). Pick a repo, branch, and optional prefix from the Actions UI.

### Packing

The source repo tells the builder what to ship via **`.github/pack.txt`** — one entry per line:

```

META-INF
isolator
system
customize.sh
module.prop
post-fs-data.sh
uninstall.sh

```

- Folders are copied **recursively** (`isolator/` brings `isolator/config.prop`, etc.).
- If **no** entry exists, the build fails (won't publish an empty zip).
- If **no** `.github/pack.txt` exists, a fallback is used:
  `META-INF webroot customize.sh post-fs-data.sh module.prop uninstall.sh service.sh`

### Versioning

- **Branch tip build** → `C<total commits>` (e.g. `C50`)
- **SHA build** (not the tip) → `P<commit count - 1>` (e.g. building #49 of 50 → `P49`)
- **`versionCode`** → current IST time as `HHMMDD` in 12-hour format (e.g. 11:58 on the 10th → `115810`)
- **Zip name** → `<PREFIX>_<C/P><n>_<sha>_by_<owner>.zip`

### Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `repo` | `RipperHybrid/sbx` | Source repo (choose or `custom`). |
| `branch` | `ExLooper` | Branch (choose or `Custom`). |
| `custom_repo` | *(empty)* | Repo path if `repo = RipperHybrid/custom`. |
| `custom_branch` | *(empty)* | Branch name if `branch = Custom`. |
| `target_commit` | *(empty)* | SHA to build instead of the branch tip. |
| `cleanup_keep` | `0` | Completed runs to keep after the build. |
| `prefix` | *(repo name)* | Release label and zip prefix. |

## Cleanup

The **Cleanup** workflow can be run by hand from the Actions tab to purge old runs from this repo or any other. Inputs:

| Input | Default | Target | Meaning |
| --- | --- | --- | --- |
| `cleanup` | `actions` | **All** | What to clean (`actions`, `releases`, or `both`). |
| `repo` | `RipperHybrid/CI` | **All** | Repo to clean. Leave empty for this repo. |
| `run_id` | *(latest)* | **Actions** | Run to wait for before cleaning. |
| `branch` | `Master` | **Actions** | Only clean runs of this branch. Empty = all. |
| `keep` | `2` | **Actions** | Runs to keep per workflow. `0` deletes everything completed. |
| `releases_to_delete` | *(empty)* | **Releases** | Delete releases: `X` = oldest, `+X` = newest, `-1` = all. |
| `delete_tags` | `true` | **Releases** | Also delete the associated git tags. |

It never deletes itself and skips running runs. Builds trigger it automatically with `CLEANUP_KEEP=0`, so nothing survives a build except the cleanup run.

## FAQ

**Can I download the builds?** No.
**Can I see what's being built?** No.
**Can I contribute?** Nothing here to contribute to.

---

*Built with mild paranoia and a lot of YAML.* ☕