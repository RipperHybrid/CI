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