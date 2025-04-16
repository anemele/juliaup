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
from dataclasses import dataclass, fields
from typing import Literal, Sequence

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


type SEQ_RELEASE = Sequence[Release]


# See: https://github.com/Fatal1ty/mashumaro/issues/69
# See: https://github.com/Fatal1ty/mashumaro/issues/69#issuecomment-1819369289
# The author said there is a solution, but I found it is not working.
# So I use the following workaround.
@dataclass
class Wrapper(DataClassORJSONMixin):
    releases: SEQ_RELEASE

    @classmethod
    def from_bytes(cls, b: bytes) -> SEQ_RELEASE:
        fc = b'{"releases":' + b + b"}"
        return cls.from_json(fc).releases


def get_two_repo_releases() -> tuple[SEQ_RELEASE, SEQ_RELEASE]:
    session = requests.Session()
    url = get_api_url("JuliaLang/juliaup")
    data1 = session.get(url)
    url = get_api_url("anemele/juliaup")
    data2 = session.get(url)

    return Wrapper.from_bytes(data1.content), Wrapper.from_bytes(data2.content)


# tag_name, name
type TODO_INFO = tuple[str, str]


def compare_and_decide(r1: SEQ_RELEASE, r2: SEQ_RELEASE) -> TODO_INFO | None:
    if len(r1) == 0:
        return None

    def find_latest_not_prerelease(rs: SEQ_RELEASE) -> Release | None:
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


@dataclass
class GitHubOutput:
    hasnew: Literal["true", "false"] = "false"
    tag: str = ""
    name: str = ""

    def __str__(self):
        arr = []
        for filed in fields(self):
            arr.append(f"{filed.name}={getattr(self, filed.name)}")
        return "\n".join(arr)


def get_output() -> GitHubOutput:
    r1, r2 = get_two_repo_releases()
    todo = compare_and_decide(r1, r2)
    if todo is None:
        return GitHubOutput()
    else:
        return GitHubOutput("true", todo[0], todo[1])


def main():
    output = get_output()

    filename = os.environ.get("GITHUB_OUTPUT", "debug.txt")
    with open(filename, "a") as fp:
        fp.write(str(output))
        fp.write("\n")


if __name__ == "__main__":
    main()
