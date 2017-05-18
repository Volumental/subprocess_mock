# -*- coding: utf-8 -*-
# Copyright 2017 Volumental AB. CONFIDENTIAL. DO NOT REDISTRIBUTE.
r"""subprocess_mock - Easy mocking of the subprocess module

The following will patch the subprocess module so that no new processes are spawned.

    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=0)
        subprocess.check_call(['ls', '-l'])

"""
import io
from typing import Tuple, List, Any, Union, Callable
from unittest.mock import patch
import re
import os

import subprocess


Command = Union[List[str], str]
SideEffect = Callable[[Command, io.StringIO, io.StringIO, io.StringIO], int]


class Expectation(object):
    def __init__(self, command: Command,
                 stdout: str, stderr: str, returncode: int, duration: int,
                 side_effect: SideEffect) -> None:
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration = duration
        self.invoke_count = 0
        self.side_effect = side_effect

    def matches(self, command: Command):
        if len(self.command) != len(command):
            return False
        if self.command == command:
            return True
        return all(re.match(pattern, c) for pattern, c in zip(self.command, command))

    def on_invoke(self):
        self.invoke_count += 1


def create_file_like(contents: Union[str, bytes]):
    r, w = os.pipe()
    with os.fdopen(w, 'w') as tmp:
        tmp.write(contents)
    return os.fdopen(r, 'r')


class FakeProcess(object):
    def __init__(self, args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None,
                 universal_newlines=False, startupinfo=None, creationflags=0) -> None:
        self.expectation = None  # type: Expectation
        self.args = args
        self.universal_newlines = universal_newlines

        self.stdout = stdout
        self.stderr = stderr

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    # NOTE: These are not to be taken as arguments to __init__ to detect problems when Popen
    # are called with wrong arguments. E.g. calling Popen with `returncode` argument must fail test
    def _setup(self, command: Command, expectation: Expectation):
        self.expectation = expectation

        if expectation.side_effect:
            stdout = io.StringIO()
            stderr = io.StringIO()
            stdin = io.StringIO()  # not supported
            expectation.returncode = expectation.side_effect(command, stdin, stdout, stderr)
            expectation.stdout = stdout.getvalue()
            expectation.stderr = stderr.getvalue()

        # Set the attributes needed
        self.returncode = self.expectation.returncode

        if self.stdout == subprocess.PIPE:
            self.stdout = create_file_like(self.expectation.stdout or '')
        else:
            self.stdout = self.expectation.stdout

        if self.stderr == subprocess.PIPE:
            self.stderr = create_file_like(self.expectation.stderr or '')
        else:
            self.stderr = self.expectation.stderr

    def communicate(self, input=None, timeout: int=None) ->\
            Tuple[Union[str, bytes], Union[str, bytes]]:
        def encode_or_none(s: str) -> Union[str, bytes]:
            """Encodes the str if needed"""
            if s is None:
                return None
            if self.universal_newlines:
                return s
            return s.encode('utf-8')

        def read_or_none(o):
            if o is None:
                return None
            if isinstance(o, str) or isinstance(o, bytes):
                return o
            return o.read()

        return encode_or_none(read_or_none(self.stdout)), encode_or_none(read_or_none(self.stderr))

    def poll(self):
        return self.expectation.returncode

    def wait(self, timeout: int=None) -> int:
        if timeout and self.expectation.duration > timeout:
            raise subprocess.TimeoutExpired(self.args, timeout)  # type: ignore

        return self.expectation.returncode

    def kill(self) -> None:
        pass


def format_command(command: Command) -> str:
    if isinstance(command, str):
        return command
    return ' '.join(command)


class SubprocessMock(object):
    def __init__(self) -> None:
        # TODO(samuel): Actually the type is `_patch`
        self.expected = []  # type: List[Expectation]
        self.popen_patch = None  # type: Any

    def __enter__(self):
        if self.popen_patch:
            self.popen_patch.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.popen_patch:
            return self.popen_patch.__exit__(exc_type, exc_val, exc_tb)
        return None

    def Popen(self, command: Command, *args, **kwargs) -> FakeProcess:
        matching = next((e for e in self.expected if e.matches(command)), None)
        if matching:
            matching.on_invoke()
            fake_process = FakeProcess(command, *args, **kwargs)
            fake_process._setup(command, matching)
            return fake_process

        error_message = "Unexpected process spawned:\n\n{}\n\nExpected one of:\n\n{}\n\n".format(
            format_command(command), '\n\n'.join([format_command(e.command) for e in self.expected]))
        hint = "Try `mock.expect({})`".format(repr(command))
        assert False, "{error_message}. {hint}".format(error_message=error_message, hint=hint)

    def expect(self, command: Command,
               stdout: str=None, stderr: str=None, returncode: int=0, duration: int=0,
               side_effect=None) -> None:
        # TODO: if side_effect is set stdout, stderr and returncode must not
        assert side_effect is None or (stdout is None and stderr is None), \
            "stdout, stderr, and returncode must not be set when using side_effect"

        expectation = Expectation(command, stdout, stderr, returncode, duration, side_effect)
        self.expected.append(expectation)

    def verify(self):
        """Asserts all expected subprocesses were called at least once"""
        for e in self.expected:
            if e.invoke_count == 0:
                raise AssertionError(
                    "Subprocess never invoked: {0}".format(format_command(e.command)))


def patch_subprocess() -> SubprocessMock:
    mock = SubprocessMock()
    mock.popen_patch = patch('subprocess.Popen', mock.Popen)
    return mock
