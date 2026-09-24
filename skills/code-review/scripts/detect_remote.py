#!/usr/bin/env python3
"""Identify the PR host of a git remote for the `code-review` skill.

    detect_remote.py [--remote NAME] [--url URL]

Prints one JSON object and exits 0 for a supported host:

    {"platform": "github", "host": "github.com", "owner": "octocat", "repo": "hello-world"}
    {"platform": "ado", "host": "dev.azure.com", "org": "fabrikam", "project": "Fiber", "repo": "web"}

An SSH host alias (a `Host` entry in ~/.ssh/config) is resolved to its real
hostname with `ssh -G` before matching, so `git@github-work:o/r.git` is GitHub.
Azure DevOps Services only: `dev.azure.com`, `ssh.dev.azure.com`, and the legacy
`*.visualstudio.com` forms. Anything else — including an on-prem Azure DevOps
Server `/_git/` URL — exits 2 with {"fatal": ...}.
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.parse

SCP_RE = re.compile(r"^(?:(?P<user>[^@/]+)@)?(?P<host>[^:/]+):(?P<path>.+)$")


def split_remote(url):
    """Return (host, path) for an https/ssh URL or scp-style `user@host:path`."""
    if "://" in url:
        parsed = urllib.parse.urlsplit(url)
        return parsed.hostname or "", parsed.path.lstrip("/")
    match = SCP_RE.match(url)
    if not match:
        return "", ""
    return match.group("host"), match.group("path").lstrip("/")


def resolve_ssh_alias(host):
    try:
        proc = subprocess.run(
            ["ssh", "-G", host], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return host
    if proc.returncode != 0:
        return host
    for line in proc.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "hostname" and value.strip():
            return value.strip().lower()
    return host


def segments(path):
    trimmed = path[:-4] if path.endswith(".git") else path
    return [urllib.parse.unquote(part) for part in trimmed.split("/") if part]


def classify(host, path):
    host = host.lower()
    parts = segments(path)

    if host == "github.com" and len(parts) == 2:
        return {"platform": "github", "host": host, "owner": parts[0], "repo": parts[1]}

    if host == "dev.azure.com" and len(parts) == 4 and parts[2] == "_git":
        return ado(parts[0], parts[1], parts[3])

    if host in ("ssh.dev.azure.com", "vs-ssh.visualstudio.com") and len(parts) == 4 and parts[0] == "v3":
        return ado(parts[1], parts[2], parts[3])

    if host.endswith(".visualstudio.com") and "_git" in parts:
        org = host[: -len(".visualstudio.com")]
        index = parts.index("_git")
        before = [p for p in parts[:index] if p.lower() != "defaultcollection"]
        if len(before) == 1 and index == len(parts) - 2:
            return ado(org, before[0], parts[index + 1])

    return None


def ado(org, project, repo):
    return {"platform": "ado", "host": "dev.azure.com", "org": org, "project": project, "repo": repo}


def detect(url):
    host, path = split_remote(url)
    if not host:
        return None
    result = classify(host, path)
    is_ssh = "://" not in url or url.startswith("ssh://")
    if result is None and is_ssh:
        result = classify(resolve_ssh_alias(host), path)
    return result


def remote_url(name):
    proc = subprocess.run(
        ["git", "remote", "get-url", name], capture_output=True, text=True
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Identify a git remote's PR host.")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--url", help="classify this URL instead of reading the remote")
    args = parser.parse_args(argv)

    url = args.url or remote_url(args.remote)
    if not url:
        print(json.dumps({"fatal": f"no git remote named '{args.remote}'"}))
        return 2
    result = detect(url)
    if result is None:
        print(json.dumps({"fatal": "unsupported remote — only github.com and Azure DevOps Services are supported", "url": url}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
