"""For JuliaLang/juliaup MSVC build

Request the releases from GitHub API, compare the two repos' releases.
Let their repo name be A, and mine be B. B does not only contain prerelease.
If len(A) == 0, do nothing.
If len(B) == 0, find the latest NOT prerelease in A, and create it in B.
Find the latest NOT prerelease in A, compared with the latest release in B.
If the version of A is bigger than B, create it in B.
Else, do nothing.

The GITHUB_OUTPUT example is:
hasnew=true
tag=v1.17.13
name=v1.17.13
"""

import os
from dataclasses import dataclass
from typing import Literal

import requests
from mashumaro.mixins.orjson import DataClassORJSONMixin
from semver.version import Version


def get_api_url(repo: str) -> str:
    """repo is owner/repo"""
    return f"https://api.github.com/repos/{repo}/releases"


@dataclass
class Release:
    tag_name: str
    name: str
    draft: bool
    prerelease: bool


@dataclass
class Wrapper(DataClassORJSONMixin):
    releases: list[Release]


def get_two_repo_releases() -> tuple[Wrapper, Wrapper]:
    session = requests.Session()
    url = get_api_url("JuliaLang/juliaup")
    data1 = session.get(url)
    url = get_api_url("anemele/juliaup")
    data2 = session.get(url)

    def wrap(c: bytes) -> Wrapper:
        fc = b'{"releases":' + c + b"}"
        return Wrapper.from_json(fc)

    return wrap(data1.content), wrap(data2.content)


# tag_name, name
type DO_INFO = tuple[str, str]


def compare_and_decide(r1: list[Release], r2: list[Release]) -> DO_INFO | None:
    if len(r1) == 0:
        return None

    def find_latest_not_prerelease(rs: list[Release]) -> Release | None:
        for r in rs:
            if not r.draft and not r.prerelease:
                return r
        return None

    r = find_latest_not_prerelease(r1)
    if r is None:
        return None

    if len(r2) == 0:
        return r.tag_name, r.name

    # remove v prefix: v1.17.13
    v1 = Version.parse(r.tag_name[1:])
    v2 = Version.parse(r2[0].tag_name[1:])
    if v1 > v2:
        return r.tag_name, r.name


def get_todo():
    d1, d2 = get_two_repo_releases()
    todo = compare_and_decide(d1.releases, d2.releases)
    return todo


@dataclass
class GitHubOutput:
    hasnew: Literal["true", "false"]
    tag: str
    name: str

    def __str__(self):
        return f"hasnew={self.hasnew}\ntag={self.tag}\nname={self.name}"


def main():
    todo = get_todo()
    if todo is None:
        output = GitHubOutput("false", "", "")
    else:
        output = GitHubOutput("true", todo[0], todo[1])

    filename = os.environ["GITHUB_OUTPUT"]
    with open(filename, "a") as fp:
        fp.write(str(output))


if __name__ == "__main__":
    main()
