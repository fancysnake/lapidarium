"""A git working copy as the export archive, through dulwich: no git binary."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from dulwich import porcelain
from dulwich.errors import GitProtocolError, NotGitRepository
from dulwich.repo import Repo

from lapidarium.pacts.content import ArchiveError, ArchiveProtocol

if TYPE_CHECKING:
    from pathlib import Path

# Who the nightly export commits as; the remote sees this, not a person.
_IDENTITY = b"lapidarium <lapidarium@localhost>"


def _open(root: Path) -> Repo:
    try:
        return Repo(str(root))
    except NotGitRepository as exc:
        msg = f"{root} is not a git repository."
        raise ArchiveError(msg) from exc


class GitArchive(ArchiveProtocol):
    @override
    def check(self, root: Path) -> None:
        _open(root).close()

    @override
    def commit(self, root: Path, *, message: str) -> bool:
        with _open(root) as repo:
            # Like `git add -A`: removals are staged too.
            porcelain.add(repo)
            staged = porcelain.status(repo).staged
            if not any(staged.values()):
                return False
            porcelain.commit(
                repo, message=message, author=_IDENTITY, committer=_IDENTITY
            )
        return True

    @override
    def push(self, root: Path) -> None:
        with _open(root) as repo:
            try:
                porcelain.push(repo)
            except (GitProtocolError, NotGitRepository, OSError, ValueError) as exc:
                msg = f"Push from {root} refused."
                raise ArchiveError(msg) from exc
