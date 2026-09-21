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
5. A cleanup workflow then wipes the run from this repo. 🧹

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