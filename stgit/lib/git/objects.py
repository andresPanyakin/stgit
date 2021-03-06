# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import re

from stgit.compat import text

from .base import Immutable, ImmutableDict, NoValue, make_defaults
from .person import Person


class GitObject(Immutable):
    """Base class for all git objects. One git object is represented by at
    most one C{GitObject}, which makes it possible to compare them
    using normal Python object comparison; it also ensures we don't
    waste more memory than necessary."""


class BlobData(Immutable):
    """Represents the data contents of a git blob object."""

    def __init__(self, data):
        assert isinstance(data, bytes)
        self.bytes = data

    def commit(self, repository):
        """Commit the blob.
        @return: The committed blob
        @rtype: L{Blob}"""
        sha1 = (
            repository.run(['git', 'hash-object', '-w', '--stdin'])
            .encoding(None)
            .raw_input(self.bytes)
            .output_one_line()
        )
        return repository.get_blob(sha1)


class Blob(GitObject):
    """Represents a git blob object. All the actual data contents of the
    blob object is stored in the L{data} member, which is a
    L{BlobData} object."""

    typename = 'blob'
    default_perm = '100644'

    def __init__(self, repository, sha1):
        self._repository = repository
        self.sha1 = sha1

    def __repr__(self):  # pragma: no cover
        return 'Blob<%s>' % self.sha1

    @property
    def data(self):
        return BlobData(self._repository.cat_object(self.sha1, encoding=None))


class TreeData(Immutable):
    """Represents the data contents of a git tree object."""

    def __init__(self, entries):
        """Create a new L{TreeData} object from the given mapping from names
        (strings) to either (I{permission}, I{object}) tuples or just
        objects."""
        self.entries = ImmutableDict(self._iter_entries(entries))

    @staticmethod
    def _iter_entries(entries):
        for name, po in entries.items():
            assert '/' not in name, (
                'tree entry name contains slash: %s' % name
            )
            if isinstance(po, GitObject):
                perm, obj = po.default_perm, po
            else:
                perm, obj = po
            yield name, (perm, obj)

    def commit(self, repository):
        """Commit the tree.
        @return: The committed tree
        @rtype: L{Tree}"""
        listing = [
            '%s %s %s\t%s' % (mode, obj.typename, obj.sha1, name)
            for (name, (mode, obj)) in self.entries.items()
        ]
        sha1 = (
            repository.run(['git', 'mktree', '-z'])
            .input_nulterm(listing)
            .output_one_line()
        )
        return repository.get_tree(sha1)

    @classmethod
    def parse(cls, repository, lines):
        """Parse a raw git tree description.

        @return: A new L{TreeData} object
        @rtype: L{TreeData}"""
        entries = {}
        for line in lines:
            m = re.match(r'^([0-7]{6}) ([a-z]+) ([0-9a-f]{40})\t(.*)$', line)
            perm, type, sha1, name = m.groups()
            entries[name] = (perm, repository.get_object(type, sha1))
        return cls(entries)


class Tree(GitObject):
    """Represents a git tree object. All the actual data contents of the
    tree object is stored in the L{data} member, which is a
    L{TreeData} object."""

    typename = 'tree'
    default_perm = '040000'

    def __init__(self, repository, sha1):
        self.sha1 = sha1
        self._repository = repository
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = TreeData.parse(
                self._repository,
                self._repository.run(
                    ['git', 'ls-tree', '-z', self.sha1]
                ).output_lines('\0'),
            )
        return self._data

    def __repr__(self):  # pragma: no cover
        return 'Tree<sha1: %s>' % self.sha1


class CommitData(Immutable):
    """Represents the data contents of a git commit object."""

    def __init__(
        self,
        tree=NoValue,
        parents=NoValue,
        author=NoValue,
        committer=NoValue,
        message=NoValue,
        defaults=NoValue,
    ):
        d = make_defaults(defaults)
        self.tree = d(tree, 'tree')
        self.parents = d(parents, 'parents')
        self.author = d(author, 'author', Person.author)
        self.committer = d(committer, 'committer', Person.committer)
        self.message = d(message, 'message')

    @property
    def env(self):
        env = {}
        for p, v1 in [(self.author, 'AUTHOR'), (self.committer, 'COMMITTER')]:
            if p is not None:
                for attr, v2 in [
                    ('name', 'NAME'),
                    ('email', 'EMAIL'),
                    ('date', 'DATE'),
                ]:
                    if getattr(p, attr) is not None:
                        env['GIT_%s_%s' % (v1, v2)] = text(getattr(p, attr))
        return env

    @property
    def parent(self):
        assert len(self.parents) == 1
        return self.parents[0]

    def set_tree(self, tree):
        return type(self)(tree=tree, defaults=self)

    def set_parents(self, parents):
        return type(self)(parents=parents, defaults=self)

    def add_parent(self, parent):
        return type(self)(
            parents=list(self.parents or []) + [parent], defaults=self
        )

    def set_parent(self, parent):
        return self.set_parents([parent])

    def set_author(self, author):
        return type(self)(author=author, defaults=self)

    def set_committer(self, committer):
        return type(self)(committer=committer, defaults=self)

    def set_message(self, message):
        return type(self)(message=message, defaults=self)

    def is_nochange(self):
        return len(self.parents) == 1 and self.tree == self.parent.data.tree

    def __repr__(self):  # pragma: no cover
        if self.tree is None:
            tree = None
        else:
            tree = self.tree.sha1
        if self.parents is None:
            parents = None
        else:
            parents = [p.sha1 for p in self.parents]
        return (
            'CommitData<tree: %s, parents: %s, author: %s, committer: %s, '
            'message: "%s">'
        ) % (tree, parents, self.author, self.committer, self.message)

    def commit(self, repository):
        """Commit the commit.
        @return: The committed commit
        @rtype: L{Commit}"""
        c = ['git', 'commit-tree', self.tree.sha1]
        for p in self.parents:
            c.append('-p')
            c.append(p.sha1)
        sha1 = (
            repository.run(c, env=self.env)
            .raw_input(self.message)
            .output_one_line()
        )
        return repository.get_commit(sha1)

    @classmethod
    def parse(cls, repository, s):
        """Parse a raw git commit description.
        @return: A new L{CommitData} object
        @rtype: L{CommitData}"""
        cd = cls(parents=[])
        lines = []
        raw_lines = s.split('\n')
        # Collapse multi-line header lines
        for i, line in enumerate(raw_lines):
            if not line:
                cd = cd.set_message('\n'.join(raw_lines[i + 1:]))
                break
            if line.startswith(' '):
                # continuation line
                lines[-1] += '\n' + line[1:]
            else:
                lines.append(line)
        for line in lines:
            if ' ' in line:
                key, value = line.split(' ', 1)
                if key == 'tree':
                    cd = cd.set_tree(repository.get_tree(value))
                elif key == 'parent':
                    cd = cd.add_parent(repository.get_commit(value))
                elif key == 'author':
                    cd = cd.set_author(Person.parse(value))
                elif key == 'committer':
                    cd = cd.set_committer(Person.parse(value))
        return cd


class Commit(GitObject):
    """Represents a git commit object. All the actual data contents of the
    commit object is stored in the L{data} member, which is a
    L{CommitData} object."""

    typename = 'commit'

    def __init__(self, repository, sha1):
        self.sha1 = sha1
        self._repository = repository
        self._data = None

    @property
    def data(self):
        if self._data is None:
            self._data = CommitData.parse(
                self._repository, self._repository.cat_object(self.sha1)
            )
        return self._data

    def __repr__(self):  # pragma: no cover
        return 'Commit<sha1: %s, data: %s>' % (self.sha1, self._data)
