# 🧪 CI

Nothing to see here, move along. 👀

This repo is just a **runner**. It has no source code of its own, no releases and no build files just a few workflow files that borrow GitHub's servers and hand the results elsewhere.

## What is this?

Some of my projects are **private, test builds**. They're not ready for the public, may be broken, and aren't meant to be shared. They stay private on purpose.

Private repos get a limited number of free Actions minutes, and public ones don't. So the builds run here, and everything they produce goes back to a private place.

## How it works

1. A workflow starts here.
2. It quietly pulls the private source using a token.
3. It builds.
4. `release.py` patches the version, then handles the release, the Telegram post, and the cleanup trigger.
5. A cleanup workflow then wipes the run from this repo.

## Manual cleanup runs

Normally nothing here needs a human runs delete themselves. But the **Cleanup** workflow can also be triggered by hand from the Actions tab, e.g. to purge old runs in this repo or in any other repo. The popup only shows short labels; here's what the inputs actually do:

| Input | Default | Meaning |
| --- | --- | --- |
| `repo` | `RipperHybrid/CI` | Repo to clean — `owner/name` or a full GitHub URL. Leave empty for this repo. |
| `run_id` | *(latest)* | Run to wait for before cleaning. Leave empty and it auto-waits (up to 5 min) if the latest run is still running, so nothing gets deleted mid-build. |
| `branch` | `Master` | Only clean runs of this branch. Leave empty for all branches. |
| `keep` | `2` | Runs to keep — the newest runs **per workflow**; older ones get deleted. `0` deletes every completed run. |

The cleanup run never deletes itself and skips runs that are still running. Manual runs keep the last 2 runs per workflow; with `keep=0` everything gets wiped the Actions tab ends up with exactly one run: the cleanup that just ran. Its **Summary** tab lists everything kept and deleted.

Builds here trigger the cleanup themselves — always for **this** repo, filtered to **their own** branch. Each workflow sets its own retention via `CLEANUP_KEEP` in its env block; they all currently pass `0`, so nothing survives a build except the cleanup run itself. And if `cleanup.yml` is ever deleted, nothing breaks: builds skip cleanup with a note instead of failing.

## Why `release.py`?

Every workflow used to carry its own copy of the same ~80 lines: patch `module.prop`, compose a release/Telegram message, publish a GitHub release, notify Telegram, trigger cleanup. That's now one script, called twice per workflow:

```
python3 release.py metadata --module-prop module.prop --prefix <Name>
python3 release.py publish --source-repo <owner/repo> --branch <branch> --status <status> --zip <path> ...
```

Each workflow only keeps what's actually different about it: which repo/branch to pull and how to build it (Vite, multi-stage node build, Rust/`cross`, plain zip). Adding a new project means writing a short workflow that checks out its source, builds it, and calls `release.py` — not duplicating the release/Telegram/cleanup logic again.

## Where do updates happen?

Some projects have their own public repos. When I update those sources, the final, cleaned-up changes land there, and that's where you can see what actually changed.

Some of the workflows here build things that aren't public at all. They're private modules I made for myself or for a very specific use, and most people wouldn't have any use for them anyway, so there's no public repo for them.

The messy in-between work (half-finished ideas, "fix", "fix again", "why is this broken", "ok now it works") happens in a private repo. That's for me to know, and for you to dot, dot, dot. 🤫

## Why is the Actions tab empty?

That's the cleanup working. Finished runs get deleted, so there's nothing left to look at. 🕵️

## FAQ

**Can I download the builds?**
No. They aren't here and they aren't public.

**Can I see what's being built?**
Not from here. Finished changes for some projects show up in their own public repos. The rest are personal builds that stay private, and the messy in-progress work stays private too. 🤐

**Can I contribute or open issues?**
There's nothing here to contribute to it only holds workflow files and one shared release script.

**Is this stable?**
The builds are test builds, so probably not. Nothing from this repo is a release.

---

*Built with mild paranoia and a lot of YAML (and now less of it).* ☕