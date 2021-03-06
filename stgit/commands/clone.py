# -*- coding: utf-8 -*-
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os

from stgit.commands import common
from stgit.lib.git import clone
from stgit.lib.stack import Stack

__copyright__ = """
Copyright (C) 2009, Catalin Marinas <catalin.marinas@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, see http://www.gnu.org/licenses/.
"""

help = 'Make a local clone of a remote repository'
kind = 'repo'
usage = ['<repository> <dir>']
description = """
Clone a git repository into the local directory <dir> (using
linkstg:clone[]) and initialise the local branch "master".

This operation is for example suitable to start working using the
"tracking branch" workflow (see link:stg[1]). Other means to setup
an StGit stack are linkstg:init[] and the '--create' and '--clone'
commands of linkstg:branch[].

The target directory <dir> will be created by this command, and must
not already exist."""

args = ['repo', 'dir']
options = []

directory = common.DirectoryAnywhere()


def func(parser, options, args):
    """Clone the <repository> into the local <dir> and initialises the
    stack
    """
    if len(args) != 2:
        parser.error('incorrect number of arguments')

    repository = args[0]
    local_dir = args[1]

    if os.path.exists(local_dir):
        raise common.CmdException('"%s" exists. Remove it first' % local_dir)

    clone(repository, local_dir)
    os.chdir(local_dir)
    directory = common.DirectoryHasRepositoryLib()
    directory.setup()
    Stack.initialise(directory.repository)
