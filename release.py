#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


def slugify(s):
    out = []
    prev_dash = False
    for ch in s:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    slug = "".join(out).strip("-")
    return slug or "module"


def gh_output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def cmd_metadata(args):
    run_number = os.environ["GITHUB_RUN_NUMBER"]
    version = f"V{run_number}"
    version_code = sh("git rev-parse --short HEAD")
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]

    with open(args.module_prop) as f:
        lines = f.read().splitlines()

    out = []
    for line in lines:
        if line.startswith("version="):
            out.append(f"version={version}")
        elif line.startswith("versionCode="):
            out.append(f"versionCode={version_code}")
        else:
            out.append(line)

    with open(args.module_prop, "w") as f:
        f.write("\n".join(out) + "\n")

    gh_output("version", version)
    gh_output("filename", f"{args.prefix}_{version}_{version_code}_by_{owner}.zip")


def compose(branch, source_repo, version, runtime, run_number, as_html):
    repo_name = source_repo.split("/", 1)[1]
    ci_name = os.environ["GITHUB_REPOSITORY"].split("/", 1)[1]
    commit_msg = sh("git log -1 --pretty=%B")
    commit_hash = sh("git rev-parse HEAD")
    commit_url = f"{os.environ['GITHUB_SERVER_URL']}/{source_repo}/commit/{commit_hash}"

    if as_html:
        if len(commit_msg) > 700:
            msg = commit_url
        else:
            msg = commit_msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out = f"Repo: <b>{repo_name}</b> [{branch}]\n"
        out += f"Run from: {ci_name} (#{run_number})\n\n"
        out += "☢️ Dev Build\n\n"
        out += f"<pre>Commit\n{msg}</pre>\n"
    else:
        out = f"Repo: **{repo_name}** [{branch}]\n"
        out += f"Run from: {ci_name} (#{run_number})\n\n"
        out += "☢️ Dev Build\n\n"
        out += f"Commit\n````\n{commit_msg}\n````\n\n"

    out += f"Version: {version or 'n/a'}\n"
    out += f"Build Time: {runtime}\n"
    return out


def send_telegram(bot_token, chat_id, zip_path, source_repo, tag, has_log):
    repo_url = f"{os.environ['GITHUB_SERVER_URL']}/{source_repo}"
    buttons = [
        {"text": "Release 📦", "url": f"{repo_url}/releases/tag/{tag}"},
        {"text": "Repo 🏠", "url": repo_url},
    ]
    if has_log:
        buttons.append({"text": "Log ⚒️", "url": f"{repo_url}/releases/download/{tag}/{tag}.log"})
    keyboard = json.dumps({"inline_keyboard": [buttons]})

    with open("/tmp/tg_caption.txt") as f:
        caption = f.read()

    subprocess.run([
        "curl", "-s", "-o", "/dev/null",
        "--form-string", f"chat_id={chat_id}",
        "-F", f"document=@{zip_path}",
        "--form-string", f"caption={caption}",
        "--form-string", "parse_mode=HTML",
        "--form-string", f"reply_markup={keyboard}",
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
    ])


def cmd_publish(args):
    run_number = os.environ["GITHUB_RUN_NUMBER"]
    display_name = args.name or args.branch

    runtime = "?"
    if args.start_ts_file and os.path.exists(args.start_ts_file):
        with open(args.start_ts_file) as f:
            d = int(time.time()) - int(f.read().strip())
        runtime = f"{d // 60}m {d % 60}s"

    notes = compose(args.branch, args.source_repo, args.version, runtime, run_number, False)
    caption = compose(args.branch, args.source_repo, args.version, runtime, run_number, True)

    with open("/tmp/notes.md", "w") as f:
        f.write(notes)
    with open("/tmp/tg_caption.txt", "w") as f:
        f.write(caption)

    tag = f"{slugify(display_name)}-{run_number}"
    sha = sh("git rev-parse HEAD")

    files = []
    has_log = False
    if args.zip and os.path.exists(args.zip):
        files.append(args.zip)
    if args.log and os.path.exists(args.log):
        log_copy = f"/tmp/{tag}.log"
        with open(args.log) as src, open(log_copy, "w") as dst:
            dst.write(src.read())
        files.append(log_copy)
        has_log = True

    title = f"{display_name} #{run_number}"
    if args.status != "success":
        title = f"[FAILED] {title}"

    subprocess.run(
        ["gh", "release", "delete", tag, "--repo", args.source_repo, "--cleanup-tag", "-y"],
        capture_output=True,
    )
    release = subprocess.run(
        ["gh", "release", "create", tag, *files,
         "--repo", args.source_repo, "--target", sha,
         "--title", title, "--notes-file", "/tmp/notes.md"],
        capture_output=True, text=True,
    )
    if release.returncode != 0:
        print(f"release failed: {release.stderr.strip()}", file=sys.stderr)

    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if bot_token and chat_id and args.zip and os.path.exists(args.zip):
        send_telegram(bot_token, chat_id, args.zip, args.source_repo, tag, has_log)

    subprocess.run(
        ["gh", "workflow", "run", "cleanup.yml",
         "--repo", os.environ["GITHUB_REPOSITORY"],
         "-f", f"run_id={os.environ['GITHUB_RUN_ID']}"],
        capture_output=True,
    )

    sys.exit(1 if release.returncode != 0 else 0)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_meta = sub.add_parser("metadata")
    p_meta.add_argument("--module-prop", required=True)
    p_meta.add_argument("--prefix", required=True)
    p_meta.set_defaults(func=cmd_metadata)

    p_pub = sub.add_parser("publish")
    p_pub.add_argument("--source-repo", required=True)
    p_pub.add_argument("--branch", required=True)
    p_pub.add_argument("--name", default="")
    p_pub.add_argument("--version", default="")
    p_pub.add_argument("--status", required=True)
    p_pub.add_argument("--zip", default="")
    p_pub.add_argument("--log", default="")
    p_pub.add_argument("--start-ts-file", default="")
    p_pub.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()