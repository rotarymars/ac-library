#!/usr/bin/env python3

import re
import sys
import argparse
from logging import Logger, basicConfig, getLogger
from os import getenv, environ, pathsep
from pathlib import Path
from typing import List, Set, Optional


logger = getLogger(__name__)  # type: Logger


class Expander:
    atcoder_include = re.compile(
        r'#include\s*["<](template/[a-z_0-9]*(|.hpp))[">]\s*')
    atcoder_include_2 = re.compile(
        r'#include\s*["<](atcoder/[a-z_0-9]*(|.hpp))[">]\s*')

    include_guard = re.compile(r'#.*ATCODER_[A-Z_]*_HPP')

    def is_ignored_line(self, line) -> bool:
        if self.include_guard.match(line):
            return True
        if line.strip() == "#pragma once":
            return True
        if line.strip().startswith('//'):
            return True
        return False

    def __init__(self, lib_paths: List[Path]):
        self.lib_paths = lib_paths

    included = set()  # type: Set[Path]

    def find_acl(self, acl_name: str) -> Path:
        for lib_path in self.lib_paths:
            path = lib_path / acl_name
            if path.exists():
                return path
        logger.error('cannot find: {}'.format(acl_name))
        raise FileNotFoundError()

    def expand_acl(self, acl_file_path: Path) -> List[str]:
        if acl_file_path in self.included:
            logger.info('already included: {}'.format(acl_file_path.name))
            return []
        self.included.add(acl_file_path)
        logger.info('include: {}'.format(acl_file_path.name))

        acl_source = open(str(acl_file_path)).read()

        result = []  # type: List[str]
        result.append("#line 1 \"" + str(acl_file_path) + "\"")
        for line in acl_source.splitlines():
            # if self.is_ignored_line(line):
            #     continue

            m = self.atcoder_include.match(line) or self.atcoder_include_2.match(line)
            if m:
                name = m.group(1)
                result.extend(self.expand_acl(self.find_acl(name)))
                continue

            result.append(line)
        return result

    def expand(self, source: str, origname) -> str:
        self.included = set()
        result = []  # type: List[str]
        linenum = 0
        for line in source.splitlines():
            linenum += 1
            m = self.atcoder_include.match(line)
            m2 = self.atcoder_include_2.match(line)
            if m or m2:
                acl_path = self.find_acl(m.group(1) if m else m2.group(1))
                result.extend(self.expand_acl(acl_path))
                if origname:
                    result.append('#line ' + str(linenum + 1) + ' "' + origname + '"')
                continue

            result.append(line)
        return '\n'.join(result)


if __name__ == "__main__":
    basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        level=getenv('LOG_LEVEL', 'INFO'),
    )
    parser = argparse.ArgumentParser(description='Expander')
    parser.add_argument('source', help='Source File')
    parser.add_argument('-c', '--console',
                        action='store_true', help='Print to Console')
    parser.add_argument('--lib', help='Path to Atcoder Library')
    parser.add_argument('--origname', help='report line numbers from the original ' +
                                           'source file in GCC/Clang error messages')
    opts = parser.parse_args()

    lib_paths = []
    if opts.lib:
        lib_paths.append(Path(opts.lib))
    if 'CPLUS_INCLUDE_PATH' in environ:
        lib_paths.extend(
            map(Path, filter(None, environ['CPLUS_INCLUDE_PATH'].split(pathsep))))
    lib_paths.append(Path.cwd())
    expander = Expander(lib_paths)
    source = open(opts.source).read()
    output = expander.expand(source, opts.origname)

    if opts.console:
        print(output)
    else:
        with open('combined.cpp', 'w') as f:
            f.write(output)
