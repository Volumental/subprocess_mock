# -*- coding: utf-8 -*-
# Copyright 2016 Volumental AB. CONFIDENTIAL. DO NOT REDISTRIBUTE.
import subprocess
from nose.tools import assert_equal, raises

import test.utils.subprocess_mock as subprocess_mock


def test_patch_restored():
    original = subprocess.Popen
    with subprocess_mock.patch_subprocess():
        pass
    assert_equal(original, subprocess.Popen)


def test_check_call_success():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], stdout="FOOBAR", returncode=0)
        subprocess.check_call(['ls', '-l'])


@raises(subprocess.CalledProcessError)
def test_check_call_failure():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=-1)
        subprocess.check_call(['ls', '-l'])


def test_check_ouput_success():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], stdout="FOOBAR", returncode=0)
        stdout = subprocess.check_output(['ls', '-l'])
        assert_equal(stdout, "FOOBAR")


@raises(subprocess.CalledProcessError)
def test_check_ouput_failure():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=-1)
        subprocess.check_output(['ls', '-l'])


# TODO(samuel): The below specific exception is correct to assert, but won't lint for some reason
#@raises(subprocess.TimeoutExpired)
@raises(subprocess.SubprocessError)
def test_timeout():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=-1, duration=10)
        p = subprocess.Popen(['ls', '-l'])
        p.wait(9)


def test_popen_communicate():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], stdout="X", stderr="Y", returncode=0)
        p = subprocess.Popen(['ls', '-l'])
        stdout, stderr = p.communicate()
        assert_equal(stdout, "X")
        assert_equal(stderr, "Y")
