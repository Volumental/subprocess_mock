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
        mock.expect(['ls', '-l'], returncode=0)
        subprocess.check_call(['ls', '-l'])


@raises(subprocess.CalledProcessError)
def test_check_call_failure():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=-1)
        subprocess.check_call(['ls', '-l'])


@raises(AssertionError)
def test_unexpected_popen():
    with subprocess_mock.patch_subprocess():
        subprocess.check_call(['ls', '-l'])


def test_check_ouput_success():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], stdout="FOOBAR", returncode=0)
        stdout = subprocess.check_output(['ls', '-l'])
        assert_equal(stdout, b'FOOBAR')


@raises(subprocess.CalledProcessError)
def test_check_ouput_failure():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=-1)
        subprocess.check_output(['ls', '-l'])


@raises(subprocess.TimeoutExpired)  # type: ignore
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
        assert_equal(stdout, b'X')
        assert_equal(stderr, b'Y')


def test_popen_communicate_universal_newlines():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], stdout="X", stderr="Y", returncode=0)
        p = subprocess.Popen(['ls', '-l'], universal_newlines=True)
        stdout, stderr = p.communicate()
        assert_equal(stdout, "X")
        assert_equal(stderr, "Y")


def test_two_expectations():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['list_serials'], returncode=0)
        mock.expect(['vandra_capture'], returncode=0)

        subprocess.check_call(['list_serials'])
        subprocess.check_call(['vandra_capture'])


def test_regexp_match():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['cmd', '--flag=.+'], returncode=0)
        subprocess.check_call(['cmd', '--flag=YES'])


@raises(AssertionError)
def test_regexp_no_match():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['cmd', '--flag=.+'], returncode=0)
        subprocess.check_call(['cmd', '--wrong=YES'])


@raises(AssertionError)
def test_too_few_args():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['cmd', '--flag=.+'], returncode=0)
        subprocess.check_call(['cmd'])


@raises(AssertionError)
def test_too_many_args():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['cmd', '--flag=.+'], returncode=0)
        subprocess.check_call(['cmd', '--flag=YES', '--unexpected'])


def test_string_command():
    with subprocess_mock.patch_subprocess() as mock:
        mock.expect('just_a_string', returncode=0)
        subprocess.check_call('just_a_string')
