# -*- coding: utf-8 -*-
# Copyright 2016 Volumental AB. CONFIDENTIAL. DO NOT REDISTRIBUTE.
from typing import Tuple, List, Any, Union
from unittest.mock import patch

import subprocess


class FakeInfo(object):
    def __init__(self, stdout: str, stderr: str, returncode: int, duration: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration = duration


class FakeProcess(object):
    def __init__(self, args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None,
                 universal_newlines=False, startupinfo=None, creationflags=0) -> None:
        self.args = args
        self.universal_newlines = universal_newlines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    # NOTE: These are not to be taken as arguments to __init__ to detect problems when Popen
    # are called with wrong arguments. E.g. calling Popen with `returncode` argument must fail test
    def _setup(self, fake_info: FakeInfo):
        self.fake_info = fake_info

    def communicate(self, input=None, timeout: int=None) -> \
            Union[Tuple[str, str], Tuple[bytes, bytes]]:
        def encode_or_none(s: str) -> bytes:
            if s:
                return s.encode('utf-8')
            return None

        if self.universal_newlines:
            return self.fake_info.stdout, self.fake_info.stderr
        return encode_or_none(self.fake_info.stdout), encode_or_none(self.fake_info.stderr)

    def poll(self):
        return self.fake_info.returncode

    def wait(self, timeout: int=None) -> int:
        if timeout and self.fake_info.duration > timeout:
            raise subprocess.TimeoutExpired(self.args, timeout)  # type: ignore

        return self.fake_info.returncode

    def kill(self) -> None:
        pass


class SubprocessMock(object):
    def __init__(self) -> None:
        # TODO(samuel): Actually the type is `_patch`
        self._popen_patch = None  # type: Any

    def __enter__(self):
        self._popen_patch.__enter__()
        self.expected = {}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._popen_patch.__exit__(exc_type, exc_val, exc_tb)

    def Popen(self, command: List[str], *args, **kwargs) -> FakeProcess:
        if repr(command) in self.expected:
            fake_process = FakeProcess(command, *args, **kwargs)
            fake_process._setup(self.expected[repr(command)])
            return fake_process

        error_message = "Unexpected process spawned: '{}'".format(' '.join(command))
        hint = "Try `mock.expect({})`".format(command)
        assert False, "{error_message}. {hint}".format(error_message=error_message, hint=hint)

    def expect(self, command: List[str],
               stdout: str=None, stderr: str=None, returncode: int=0, duration: int=0) -> None:
        self.expected[repr(command)] = FakeInfo(stdout, stderr, returncode, duration)


def patch_subprocess() -> SubprocessMock:
    mock = SubprocessMock()
    mock._popen_patch = patch('subprocess.Popen', mock.Popen)
    return mock
