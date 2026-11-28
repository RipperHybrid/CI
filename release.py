#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta


DEFAULT_HTML = (
    "Repo: <b>{repo_name}</b> [{branch}]\n"
    "Run from: {ci_name} (#{run_number})\n"
    "Commit No: {commit_no}\n"
    "Hash: {commit_short}\n\n"
    "{build_label}\n\n"
    "<pre>Commit\n{commit_msg}</pre>\n"
    "Version: {version}\n"
    "Build Time: {runtime}\n"
)

DEFAULT_MD = (
    "Repo: **{repo_name}** [{branch}]\n"
    "Run from: {ci_name} (#{run_number})\n"
    "Commit No: {commit_no}\n"
    "Hash: {commit_short}\n\n"
    "{build_label}\n\n"
    "Commit\n````\n{commit_msg}\n````\n\n"
    "Version: {version}\n"
    "Build Time: {runtime}\n"
)


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


def tag_safe(s):
    out = []
    for ch in s:
        if ch.isalnum() or ch in "._-":
            out.append(ch)
        else:
            out.append("-")
    return "".join(out).strip("-.")


def html_escape(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def gh_output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"{key}={value}\n")


def ist_version_code():
    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)
    hour12 = now.hour % 12 or 12
    return f"{hour12:02d}{now.minute:02d}{now.day:02d}"


def read_module_name(prop_path):
    try:
        with open(prop_path) as f:
            for line in f:
                if line.startswith("name="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def cmd_metadata(args):
    run_number = os.environ["GITHUB_RUN_NUMBER"]
    commit_hash = sh("git rev-parse HEAD")
    commit_short = sh("git rev-parse --short HEAD")
    commit_count = sh("git rev-list --count HEAD")
    if not commit_count.isdigit():
        commit_count = run_number
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]

    branch = os.environ.get("TARGET_BRANCH", "").strip()
    branch_tip = ""
    if branch:
        try:
            out = subprocess.run(
                ["git", "ls-remote", "origin", f"refs/heads/{branch}"],
                capture_output=True, text=True, check=True, timeout=10,
            ).stdout.strip()
            if out:
                branch_tip = out.split()[0]
        except Exception:
            branch_tip = ""

    target_commit = os.environ.get("TARGET_COMMIT", "").strip()
    is_sha_build = bool(
        (branch_tip and branch_tip != commit_hash)
        or (target_commit and target_commit != commit_hash and not commit_hash.startswith(target_commit))
    )

    if is_sha_build:
        version = f"P{int(commit_count) - 1}"
    else:
        version = f"C{commit_count}"

    version_code = ist_version_code()

    prefix = args.prefix.strip()
    if not prefix:
        module_name = read_module_name(args.module_prop)
        prefix = slugify(module_name) if module_name else "module"

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

    gh_output("name", prefix)
    gh_output("version", version)
    gh_output("filename", f"{prefix}_{version}_{commit_short}_by_{owner}.zip")


def read_template(args, kind):
    path = args.msg_file if kind == "msg" else args.notes_file
    if path and os.path.exists(path):
        with open(path) as f:
            return f.read()
    value = args.msg if kind == "msg" else args.notes
    if value:
        return value
    return None


def build_label(tag):
    if (tag or "").strip().lower() == "release":
        return "💎 Release Build"
    return "☢️ Dev Build"


def compose(template, *, branch, source_repo, version, runtime, run_number, as_html, tag="dev", meta=None):
    repo_name = source_repo.split("/", 1)[1]
    ci_name = os.environ["GITHUB_REPOSITORY"].split("/", 1)[1]
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    if meta is None:
        commit_msg = sh("git log -1 --pretty=%B")
        commit_hash = sh("git rev-parse HEAD")
        commit_short = sh("git rev-parse --short HEAD")
        commit_no = sh("git rev-list --count HEAD") or "n/a"
        commit_url = f"{server_url}/{source_repo}/commit/{commit_hash}"
        if as_html:
            if len(commit_msg) > 700:
                rendered = commit_url
            else:
                rendered = commit_msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        else:
            rendered = commit_url if len(commit_msg) > 700 else commit_msg
    else:
        commit_msg = str(meta.get("commit_msg") or "")
        commit_hash = str(meta.get("commit_hash") or "")
        commit_short = str(meta.get("commit_short") or "")
        commit_no = str(meta.get("commit_no") or "") or "n/a"
        run_number = str(meta.get("run_number") or run_number)
        commit_url = f"{server_url}/{source_repo}/commit/{commit_hash}"
        rendered = commit_url if len(commit_msg) > 700 else commit_msg

    values = {
        "repo_name": repo_name,
        "branch": branch,
        "ci_name": ci_name,
        "run_number": run_number,
        "commit_msg": rendered,
        "commit_url": commit_url,
        "commit_no": commit_no,
        "commit_short": commit_short,
        "commit_hash": commit_hash,
        "version": version or "n/a",
        "runtime": runtime,
        "build_label": build_label(tag),
    }
    if as_html and meta is not None:
        values = {key: html_escape(value) if isinstance(value, str) else value
                  for key, value in values.items()}
    return template.format(**values)


def resolve_buttons(args, repo_url, tag):
    if args.buttons_file and os.path.exists(args.buttons_file):
        with open(args.buttons_file) as f:
            return json.load(f)
    if args.buttons:
        return json.loads(args.buttons)

    return {"inline_keyboard": [[
        {"text": "Release 📦", "url": f"{repo_url}/releases/tag/{tag}"},
    ]]}


def send_telegram(bot_token, chat_id, zip_path, keyboard):
    with open("/tmp/tg_caption.txt") as f:
        caption = f.read()

    subprocess.run([
        "curl", "-s", "-o", "/dev/null",
        "--form-string", f"chat_id={chat_id}",
        "-F", f"document=@{zip_path}",
        "--form-string", f"caption={caption}",
        "--form-string", "parse_mode=HTML",
        "--form-string", f"reply_markup={json.dumps(keyboard)}",
        f"https://api.telegram.org/bot{bot_token}/sendDocument",
    ])


TELEGRAM_FILE_LIMIT = 49 * 1024 * 1024


def redact_command(cmd):
    return " ".join(
        "<redacted>" if "api.telegram.org/bot" in str(part) else str(part)
        for part in cmd
    )


def run_report(cmd, label):
    telegram = any("api.telegram.org/bot" in str(part) for part in cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as exc:
        if telegram:
            print(label, file=sys.stderr)
        else:
            print(f"{label} raised: {exc}", file=sys.stderr)
        return subprocess.CompletedProcess(cmd, 1, "", str(exc))
    if result.returncode != 0:
        if telegram:
            print(label, file=sys.stderr)
        else:
            print(f"{label} failed: {redact_command(cmd)}", file=sys.stderr)
            if result.stderr:
                print(result.stderr.strip(), file=sys.stderr)
    return result


def retry_command(cmd, label, attempts=3, delay=5):
    result = None
    for attempt in range(1, attempts + 1):
        result = run_report(cmd, f"{label} attempt {attempt}/{attempts}")
        if result.returncode == 0:
            return result
        if attempt < attempts:
            time.sleep(delay)
    return result


def inspect_release(tag, source_repo):
    cmd = ["gh", "release", "view", tag, "--repo", source_repo, "--json", "name,tagName"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as exc:
        print(f"release view raised: {exc}", file=sys.stderr)
        return {}
    if result.returncode == 0:
        try:
            return json.loads(result.stdout or "{}")
        except Exception as exc:
            print(f"release view parse failed: {exc}", file=sys.stderr)
            return {}
    detail = (result.stderr or result.stdout or "").strip()
    lower = detail.lower()
    if "not found" in lower or "could not resolve" in lower or "no release" in lower:
        return None
    print(f"release view failed: {redact_command(cmd)}", file=sys.stderr)
    if detail:
        print(detail, file=sys.stderr)
    return {}


def telegram_request(cmd, label):
    result = run_report(cmd, label)
    response = (result.stdout or "").strip()
    description = ""
    error_code = ""
    try:
        data = json.loads(response)
        ok = data.get("ok") is True
        description = str(data.get("description") or "")
        error_code = str(data.get("error_code") or "")
    except Exception as exc:
        ok = False
        description = f"invalid Telegram response: {exc}"
        redacted = response
        for secret in (os.environ.get("BOT_TOKEN", ""), os.environ.get("CHAT_ID", "")):
            if secret:
                redacted = redacted.replace(secret, "<redacted>")
        preview = redacted[:120].replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
        print(f"{label} invalid response length: {len(response)}", file=sys.stderr)
        print(f"{label} invalid response preview: {preview}", file=sys.stderr)
    if ok:
        print(f"{label} ok")
    else:
        print(f"{label} exit code: {result.returncode}", file=sys.stderr)
        print(f"{label} error_code: {error_code or 'n/a'}", file=sys.stderr)
        print(f"::warning::{label} description: {description or 'no description'}")
    return ok, description


def telegram_send_message(bot_token, chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    cmd = [
        "curl", "-sS", "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(payload),
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
    ]
    return telegram_request(cmd, "sendMessage")


def telegram_send_document(bot_token, chat_id, path, caption, keyboard=None):
    cmd = [
        "curl", "-sS", "-X", "POST",
        "--form-string", f"chat_id={chat_id}",
        "-F", f"document=@{path}",
        "--form-string", f"caption={caption}",
        "--form-string", "parse_mode=HTML",
    ]
    if keyboard:
        cmd += ["--form-string", f"reply_markup={json.dumps(keyboard)}"]
    cmd += [f"https://api.telegram.org/bot{bot_token}/sendDocument"]
    return telegram_request(cmd, "sendDocument")


def telegram_send_album(bot_token, chat_id, paths, caption):
    media = []
    cmd = [
        "curl", "-sS", "-X", "POST",
        "--form-string", f"chat_id={chat_id}",
    ]
    for index, path in enumerate(paths):
        item = {"type": "document", "media": f"attach://file{index}"}
        if index == 0:
            item["caption"] = caption
            item["parse_mode"] = "HTML"
        media.append(item)
        cmd += ["-F", f"file{index}=@{path}"]
    cmd += [
        "--form-string", f"media={json.dumps(media)}",
        f"https://api.telegram.org/bot{bot_token}/sendMediaGroup",
    ]
    return telegram_request(cmd, "sendMediaGroup")


def button_links(args, repo_url, tag):
    try:
        keyboard = resolve_buttons(args, repo_url, tag)
        rows = keyboard.get("inline_keyboard") or []
    except Exception as exc:
        print(f"button parsing failed: {exc}", file=sys.stderr)
        rows = [[{"text": "Release", "url": f"{repo_url}/releases/tag/{tag}"}]]
    links = []
    for row in rows:
        for button in row:
            url = str(button.get("url") or "")
            if not url:
                continue
            text = html_escape(button.get("text") or "Link")
            links.append(f'<a href="{html_escape(url)}">{text}</a>')
    return " ".join(links)


def build_deferred_buttons(args, repo_url, tag, meta, log_archive_name, run_url):
    logs_url = ""
    if log_archive_name and args.log_archive and os.path.isfile(args.log_archive):
        logs_url = f"{repo_url}/releases/download/{tag}/{log_archive_name}"
    else:
        logs_url = run_url or ""
    logs_button = {"text": "Logs 📋", "url": logs_url}

    keyboard = {}
    try:
        if args.buttons_file and os.path.exists(args.buttons_file):
            with open(args.buttons_file) as handle:
                keyboard = json.load(handle) or {}
        elif args.buttons:
            keyboard = json.loads(args.buttons) or {}
    except Exception as exc:
        print(f"button parsing failed: {exc}", file=sys.stderr)

    rows = keyboard.get("inline_keyboard") or []
    if not rows:
        commit_hash = str(meta.get("commit_hash") or "")
        commit_url = f"{repo_url}/commit/{commit_hash}"
        rows = [
            [
                {"text": "Release 📦", "url": f"{repo_url}/releases/tag/{tag}"},
                logs_button,
            ],
            [
                {"text": "Commit 🔗", "url": commit_url},
                {"text": "Repo 🏠", "url": repo_url},
            ],
        ]
    else:
        rows = list(rows)
        rows.append([logs_button])
    return {"inline_keyboard": rows}


def join_description(note, detail):
    return " ".join(part for part in (note, detail) if part)


def cmd_publish_deferred(args):
    if not args.metadata_file or not os.path.isfile(args.metadata_file):
        print(f"deferred publish: metadata file not found: {args.metadata_file}", file=sys.stderr)
        sys.exit(1)
    try:
        with open(args.metadata_file) as handle:
            meta = json.load(handle)
    except Exception as exc:
        print(f"deferred publish: cannot read metadata: {exc}", file=sys.stderr)
        sys.exit(1)

    sha = str(meta.get("commit_hash") or "").strip()
    if not sha:
        print("deferred publish: commit_hash is empty in metadata", file=sys.stderr)
        sys.exit(1)

    run_number = str(meta.get("run_number") or "")
    display_name = args.name or args.branch or str(meta.get("name") or "")
    if not display_name:
        display_name = "module"

    release_files = []
    for path in (args.zip, args.log_archive):
        if path and os.path.isfile(path):
            release_files.append(path)
    for path in release_files:
        if " " in os.path.basename(path):
            print(f"deferred publish: asset name contains a space: {path}", file=sys.stderr)
            sys.exit(1)

    version_tag = tag_safe(args.version.strip()) if args.version else ""
    tag = version_tag or f"{slugify(display_name)}-{run_number}"
    existing = inspect_release(tag, args.source_repo)
    if args.status != "success" and existing is not None:
        existing_title = str(existing.get("name") or "")
        if not existing_title.startswith("[FAILED]"):
            tag = f"{tag}-failed-{run_number}"

    html_tpl = read_template(args, "msg") or DEFAULT_HTML
    md_tpl = read_template(args, "notes") or DEFAULT_MD
    notes = compose(md_tpl, branch=args.branch, source_repo=args.source_repo,
                    version=args.version, runtime=args.runtime,
                    run_number=run_number, as_html=False, tag=args.tag, meta=meta)
    caption = compose(html_tpl, branch=args.branch, source_repo=args.source_repo,
                      version=args.version, runtime=args.runtime,
                      run_number=run_number, as_html=True, tag=args.tag, meta=meta)
    with open("/tmp/notes_deferred.md", "w") as handle:
        handle.write(notes)

    if args.version:
        title = f"{display_name} - Version {args.version} Changelog"
    else:
        title = f"{display_name} Changelog"
    if args.status != "success":
        title = f"[FAILED] {title}"

    delete_cmd = [
        "gh", "release", "delete", tag, "--repo", args.source_repo,
        "--cleanup-tag", "-y",
    ]
    delete = subprocess.run(delete_cmd, capture_output=True, text=True)
    if delete.returncode != 0:
        detail = (delete.stderr or delete.stdout or "").strip()
        if "not found" not in detail.lower() and "could not resolve" not in detail.lower():
            print(f"release delete failed: {redact_command(delete_cmd)}", file=sys.stderr)
            if detail:
                print(detail, file=sys.stderr)

    create_cmd = [
        "gh", "release", "create", tag,
        "--repo", args.source_repo,
        "--target", sha,
        "--title", title,
        "--notes-file", "/tmp/notes_deferred.md",
    ]
    release_ok = False
    create = None
    for attempt in range(1, 4):
        create = run_report(create_cmd, f"release create attempt {attempt}/3")
        if create.returncode == 0:
            release_ok = True
            break
        if attempt < 3:
            time.sleep(5)
    if not release_ok:
        gh_output("release_ok", "false")
        gh_output("telegram_ok", "false")
        gh_output("telegram_description", "release creation failed after 3 attempts")
        sys.exit(1)

    expected_assets = []
    if release_ok:
        for path in release_files:
            name = os.path.basename(path)
            expected_assets.append(name)
            upload_cmd = [
                "gh", "release", "upload", tag, path,
                "--repo", args.source_repo, "--clobber",
            ]
            uploaded = False
            for attempt in range(1, 4):
                upload = run_report(upload_cmd, f"release upload attempt {attempt}/3 for {name}")
                if upload.returncode == 0:
                    uploaded = True
                    break
                if attempt < 3:
                    time.sleep(5)
            if not uploaded:
                print(f"deferred publish: upload failed for {name}", file=sys.stderr)
        view = run_report(
            ["gh", "release", "view", tag, "--repo", args.source_repo, "--json", "assets"],
            "release view",
        )
        if view.returncode != 0:
            release_ok = False
        else:
            try:
                assets = json.loads(view.stdout or "{}").get("assets") or []
                present = {str(asset.get("name") or "") for asset in assets}
            except Exception as exc:
                print(f"release view parse failed: {exc}", file=sys.stderr)
                present = set()
            missing = [name for name in expected_assets if name not in present]
            if missing:
                print(f"deferred publish: missing release assets: {', '.join(missing)}", file=sys.stderr)
                release_ok = False

    bot_token = os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    telegram_ok = False
    telegram_description = ""
    if not bot_token or not chat_id:
        telegram_description = "BOT_TOKEN or CHAT_ID is missing"
        print(f"deferred publish: {telegram_description}", file=sys.stderr)
    else:
        repo_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{args.source_repo}"
        log_archive_name = ""
        if args.log_archive and os.path.isfile(args.log_archive):
            log_archive_name = os.path.basename(args.log_archive)
        keyboard = build_deferred_buttons(
            args, repo_url, tag, meta, log_archive_name, args.run_url,
        )
        zip_path = ""
        if args.status == "success" and args.zip and os.path.isfile(args.zip):
            zip_path = args.zip

        oversized_note = ""
        if zip_path and os.path.getsize(zip_path) > TELEGRAM_FILE_LIMIT:
            oversized_note = "Module zip omitted from Telegram: exceeds 49 MB Bot API limit"
            zip_path = ""

        description = caption.rstrip()
        if oversized_note:
            description += "\n" + oversized_note
        short_caption = (
            f"{html_escape(build_label(args.tag))}\n"
            f"Version: {html_escape(args.version or 'n/a')}"
        )
        long_description = len(description) > 1024

        if long_description:
            first_ok, first_detail = telegram_send_message(bot_token, chat_id, description)
            if zip_path:
                second_ok, second_detail = telegram_send_document(
                    bot_token, chat_id, zip_path, short_caption, keyboard,
                )
                if not second_ok:
                    second_ok, second_detail = telegram_send_message(
                        bot_token, chat_id, short_caption, keyboard,
                    )
            else:
                second_ok, second_detail = telegram_send_message(
                    bot_token, chat_id, short_caption, keyboard,
                )
            telegram_ok = first_ok and second_ok
            telegram_description = join_description(oversized_note, second_detail or first_detail)
        elif zip_path:
            telegram_ok, detail = telegram_send_document(
                bot_token, chat_id, zip_path, description, keyboard,
            )
            if not telegram_ok:
                telegram_ok, detail = telegram_send_message(
                    bot_token, chat_id, description, keyboard,
                )
            telegram_description = join_description(oversized_note, detail)
        else:
            telegram_ok, detail = telegram_send_message(
                bot_token, chat_id, description, keyboard,
            )
            telegram_description = join_description(oversized_note, detail)

    gh_output("release_ok", "true" if release_ok else "false")
    gh_output("telegram_ok", "true" if telegram_ok else "false")
    gh_output("telegram_description", telegram_description.replace("\r", " ").replace("\n", " "))
    sys.exit(0 if release_ok and telegram_ok else 1)


def cmd_publish(args):
    if args.deferred:
        cmd_publish_deferred(args)
        return
    run_number = os.environ["GITHUB_RUN_NUMBER"]
    display_name = args.name or args.branch

    runtime = "?"
    if args.start_ts_file and os.path.exists(args.start_ts_file):
        with open(args.start_ts_file) as f:
            d = int(time.time()) - int(f.read().strip())
        runtime = f"{d // 60}m {d % 60}s"

    html_tpl = read_template(args, "msg") or DEFAULT_HTML
    md_tpl = read_template(args, "notes") or DEFAULT_MD

    notes = compose(md_tpl, branch=args.branch, source_repo=args.source_repo,
                    version=args.version, runtime=runtime,
                    run_number=run_number, as_html=False, tag=args.tag)
    caption = compose(html_tpl, branch=args.branch, source_repo=args.source_repo,
                      version=args.version, runtime=runtime,
                      run_number=run_number, as_html=True, tag=args.tag)

    with open("/tmp/notes.md", "w") as f:
        f.write(notes)
    with open("/tmp/tg_caption.txt", "w") as f:
        f.write(caption)

    version_tag = tag_safe(args.version.strip()) if args.version else ""
    tag = version_tag or f"{slugify(display_name)}-{run_number}"
    sha = sh("git rev-parse HEAD")

    files = []
    if args.zip and os.path.isfile(args.zip):
        files.append(args.zip)

    if args.version:
        title = f"{display_name} - Version {args.version} Changelog"
    else:
        title = f"{display_name} Changelog"
    if args.status != "success":
        title = f"[FAILED] {title}"

    try:
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
        if bot_token and chat_id and args.zip and os.path.isfile(args.zip):
            repo_url = f"{os.environ['GITHUB_SERVER_URL']}/{args.source_repo}"
            keyboard = resolve_buttons(args, repo_url, tag)
            send_telegram(bot_token, chat_id, args.zip, keyboard)
    except Exception as e:
        print(f"publish step raised: {e}", file=sys.stderr)
        release = subprocess.CompletedProcess(args=[], returncode=1)
    finally:
        cleanup_workflow = os.path.join(
            os.environ.get("GITHUB_WORKSPACE", "."), ".github", "workflows", "cleanup.yml"
        )
        if not os.path.exists(cleanup_workflow):
            print("cleanup.yml not found skipping run cleanup", file=sys.stderr)
        else:
            repo = os.environ["GITHUB_REPOSITORY"]
            dispatch = [
                "gh", "workflow", "run", "cleanup.yml",
                "--repo", repo,
                "-f", f"repo={repo}",
                "-f", f"run_id={os.environ['GITHUB_RUN_ID']}",
            ]
            if args.cleanup_keep:
                dispatch += ["-f", f"keep={args.cleanup_keep}"]
            ref = os.environ.get("GITHUB_REF_NAME")
            if ref:
                dispatch += ["-f", f"branch={ref}"]
            try:
                cleanup = subprocess.run(dispatch, capture_output=True, text=True)
                if cleanup.returncode != 0:
                    print(f"cleanup dispatch failed (build unaffected): {cleanup.stderr.strip()}", file=sys.stderr)
            except Exception as e:
                print(f"cleanup dispatch raised: {e}", file=sys.stderr)

    sys.exit(1 if release.returncode != 0 else 0)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p_meta = sub.add_parser("metadata")
    p_meta.add_argument("--module-prop", required=True)
    p_meta.add_argument("--prefix", default="")
    p_meta.set_defaults(func=cmd_metadata)

    p_pub = sub.add_parser("publish")
    p_pub.add_argument("--source-repo", required=True)
    p_pub.add_argument("--branch", required=True)
    p_pub.add_argument("--name", default="")
    p_pub.add_argument("--version", default="")
    p_pub.add_argument("--status", required=True)
    p_pub.add_argument("--tag", default="dev")
    p_pub.add_argument("--zip", default="")
    p_pub.add_argument("--cleanup-keep", default="")
    p_pub.add_argument("--start-ts-file", default="")
    p_pub.add_argument("--msg", default="")
    p_pub.add_argument("--msg-file", default="")
    p_pub.add_argument("--notes", default="")
    p_pub.add_argument("--notes-file", default="")
    p_pub.add_argument("--buttons", default="")
    p_pub.add_argument("--buttons-file", default="")
    p_pub.add_argument("--deferred", action="store_true")
    p_pub.add_argument("--metadata-file", default="")
    p_pub.add_argument("--log", default="")
    p_pub.add_argument("--log-archive", default="")
    p_pub.add_argument("--runtime", default="")
    p_pub.add_argument("--run-url", default="")
    p_pub.set_defaults(func=cmd_publish)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
