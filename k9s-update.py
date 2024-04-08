#!/usr/bin/env python

from os import unlink
from pathlib import Path
from subprocess import run, PIPE


REPO = "derailed/k9s"
ASSET_NAME = "k9s_Linux_amd64.tar.gz"
EXECUTABLE_NAME = "k9s"
EXECUTABLE_TARGET_LOCATION = Path("/home/rlat/bin")


# Function to get current version of K9s by running `k9s version`
def current_k9s_version() -> str | None:
    try:
        output = (
            run([EXECUTABLE_NAME, "version"], check=True, stdout=PIPE, stderr=PIPE, text=True).stdout.strip().split()
        )
    except FileNotFoundError:
        return "Not installed"

    for index, line in enumerate(output):
        if "Version:" in line:
            return output[index + 1]

    return None


def gh_get_latest_release(repo: str) -> str:
    return run(
        [
            "gh",
            "release",
            "--repo",
            repo,
            "list",
            "--exclude-drafts",
            "--exclude-pre-releases",
            "--limit",
            "1",
            "--json",
            "name",
            "--jq",
            ".[].name",
        ],
        check=True,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
    ).stdout.strip()


def gh_download_asset(repo: str, release: str, asset_glob: str) -> None:
    run(["gh", "release", "--repo", repo, "download", release, "--pattern", asset_glob, "--skip-existing"], check=True)


def extract_release(filename: str, target_folder: Path) -> None:
    print(f"Extracting")
    run(["tar", "-xzf", filename, "-C", str(target_folder)], check=True)


def cleanup(filename: str) -> None:
    print(f"Cleaning up")
    unlink(filename)


def main():
    current_version = current_k9s_version()
    latest_release = gh_get_latest_release(REPO)

    print("Current version:", current_version)
    print("Latest release:", latest_release)

    if current_version == latest_release:
        print("No new releases")
        return

    gh_download_asset(REPO, latest_release, ASSET_NAME)
    extract_release(ASSET_NAME, EXECUTABLE_TARGET_LOCATION)
    cleanup(ASSET_NAME)


if __name__ == "__main__":
    main()
