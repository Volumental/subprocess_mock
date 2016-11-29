# -*- coding: utf-8 -*-
# Copyright 2016 Volumental AB. CONFIDENTIAL. DO NOT REDISTRIBUTE.
from unittest.mock import patch

import subprocess


class FakeInfo(object):
    def __init__(self, stdout, stderr, returncode, duration):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.duration = duration


class FakeProcess(object):
    def __init__(self, args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False, cwd=None, env=None,
                 universal_newlines=False, startupinfo=None, creationflags=0):
        self.args = args

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    # NOTE: These are not to be taken as arguments to __init__ to detect problems when Popen
    # are called with wrong arguments. E.g. calling Popen with `returncode` argument must fail test
    def _setup(self, fake_info):
        self.fake_info = fake_info

    def communicate(self, input=None, timeout=None):
        return self.fake_info.stdout, self.fake_info.stderr

    def poll(self):
        return self.fake_info.returncode

    def wait(self, timeout=None):
        if timeout and self.fake_info.duration > timeout:
            raise subprocess.TimeoutExpired(self.args, timeout)

        return self.fake_info.returncode

    def kill(self):
        pass


class SubprocessMock(object):
    def __enter__(self):
        self._popen_patch.__enter__()
        self.expected = {}
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._popen_patch.__exit__(exc_type, exc_val, exc_tb)

    def Popen(self, command, *args, **kwargs):
        if repr(command) in self.expected:
            fake_process = FakeProcess(command, *args, **kwargs)
            fake_process._setup(self.expected[repr(command)])
            return fake_process

        error_message = "Unexpected process spawned: '{}'".format(' '.join(command))
        hint = "Try `mock.expect({})`".format(command)
        assert False, "{error_message}. {hint}".format(error_message=error_message, hint=hint)

    def expect(self, command, stdout=None, stderr=None, returncode=0, duration=0):
        self.expected[repr(command)] = FakeInfo(stdout, stderr, returncode, duration)


def patch_subprocess():
    mock = SubprocessMock()
    mock._popen_patch = patch('subprocess.Popen', mock.Popen)
    return mock
