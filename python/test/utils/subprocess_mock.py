# -*- coding: utf-8 -*-
# Copyright 2016 Volumental AB. CONFIDENTIAL. DO NOT REDISTRIBUTE.
r"""subprocess_mock - Easy mocking of the subprocess module

The following will patch the subprocess module so that no new processes are spawned.

    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=0)
        subprocess.check_call(['ls', '-l'])

"""
from typing import Tuple, List, Any, Union
from unittest.mock import patch
import re

import subprocess


class Expectation(object):
    def __init__(self, command: List[str],
                 stdout: str, stderr: str, returncode: int, duration: int) -> None:
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration = duration

    def matches(self, command: List[str]):
        if len(self.command) != len(command):
            return False
        return all(re.match(pattern, c) for pattern, c in zip(self.command, command))


class FakeProcess(object):
    def __init__(self, args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None,
                 universal_newlines=False, startupinfo=None, creationflags=0) -> None:
        self.expectation = None  # type: Expectation
        self.args = args
        self.universal_newlines = universal_newlines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    # NOTE: These are not to be taken as arguments to __init__ to detect problems when Popen
    # are called with wrong arguments. E.g. calling Popen with `returncode` argument must fail test
    def _setup(self, expectation: Expectation):
        self.expectation = expectation

    def communicate(self, input=None, timeout: int=None) -> \
            Union[Tuple[str, str], Tuple[bytes, bytes]]:
        def encode_or_none(s: str) -> bytes:
            if s:
                return s.encode('utf-8')
            return None

        if self.universal_newlines:
            return self.expectation.stdout, self.expectation.stderr
        return encode_or_none(self.expectation.stdout), encode_or_none(self.expectation.stderr)

    def poll(self):
        return self.expectation.returncode

    def wait(self, timeout: int=None) -> int:
        if timeout and self.expectation.duration > timeout:
            raise subprocess.TimeoutExpired(self.args, timeout)  # type: ignore

        return self.expectation.returncode

    def kill(self) -> None:
        pass


class SubprocessMock(object):
    def __init__(self) -> None:
        # TODO(samuel): Actually the type is `_patch`
        self.expected = []  # type: List[Expectation]
        self._popen_patch = None  # type: Any

    def __enter__(self):
        if self._popen_patch:
            self._popen_patch.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._popen_patch:
            return self._popen_patch.__exit__(exc_type, exc_val, exc_tb)
        return None

    def Popen(self, command: List[str], *args, **kwargs) -> FakeProcess:
        matching = next((e for e in self.expected if e.matches(command)), None)
        if matching:
            fake_process = FakeProcess(command, *args, **kwargs)
            fake_process._setup(matching)
            return fake_process

        error_message = "Unexpected process spawned: '{}'".format(' '.join(command))
        hint = "Try `mock.expect({})`".format(command)
        assert False, "{error_message}. {hint}".format(error_message=error_message, hint=hint)

    def expect(self, command: List[str],
               stdout: str=None, stderr: str=None, returncode: int=0, duration: int=0) -> None:
        self.expected.append(Expectation(command, stdout, stderr, returncode, duration))


def patch_subprocess() -> SubprocessMock:
    mock = SubprocessMock()
    mock._popen_patch = patch('subprocess.Popen', mock.Popen)
    return mock
