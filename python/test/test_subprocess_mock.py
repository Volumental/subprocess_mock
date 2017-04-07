# -*- coding: utf-8 -*-
# Copyright 2017 Volumental AB. CONFIDENTIAL. DO NOT REDISTRIBUTE.
import subprocess
from unittest import TestCase

from nose.tools import assert_equal, raises

import test.utils.subprocess_mock as subprocess_mock


class TestSubprocessMock(TestCase):

    def test_patch_restored(self):
        original = subprocess.Popen
        with subprocess_mock.patch_subprocess():
            pass
        assert_equal(original, subprocess.Popen)

    def test_check_call_success(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], returncode=0)
            subprocess.check_call(['ls', '-l'])

    @raises(subprocess.CalledProcessError)
    def test_check_call_failure(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], returncode=-1)
            subprocess.check_call(['ls', '-l'])

    @raises(AssertionError)
    def test_unexpected_popen(self):
        with subprocess_mock.patch_subprocess():
            subprocess.check_call(['ls', '-l'])

    def test_check_ouput_success(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], stdout="FOOBAR", returncode=0)
            stdout = subprocess.check_output(['ls', '-l'])
            assert_equal(stdout, b'FOOBAR')

    @raises(subprocess.CalledProcessError)
    def test_check_ouput_failure(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], returncode=-1)
            subprocess.check_output(['ls', '-l'])

    @raises(subprocess.TimeoutExpired)  # type: ignore
    def test_timeout(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], returncode=-1, duration=10)
            p = subprocess.Popen(['ls', '-l'])
            p.wait(9)

    def test_popen_communicate(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], stdout="X", stderr="Y", returncode=0)
            p = subprocess.Popen(['ls', '-l'])
            stdout, stderr = p.communicate()
            assert_equal(stdout, b'X')
            assert_equal(stderr, b'Y')

    def test_popen_communicate_universal_newlines(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['ls', '-l'], stdout="X", stderr="Y", returncode=0)
            p = subprocess.Popen(['ls', '-l'], universal_newlines=True)
            stdout, stderr = p.communicate()
            assert_equal(stdout, "X")
            assert_equal(stderr, "Y")

    def test_two_expectations(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['list_serials'], returncode=0)
            mock.expect(['vandra_capture'], returncode=0)

            subprocess.check_call(['list_serials'])
            subprocess.check_call(['vandra_capture'])

    def test_regexp_match(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['cmd', '--flag=.+'], returncode=0)
            subprocess.check_call(['cmd', '--flag=YES'])

    @raises(AssertionError)
    def test_regexp_no_match(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['cmd', '--flag=.+'], returncode=0)
            subprocess.check_call(['cmd', '--wrong=YES'])

    @raises(AssertionError)
    def test_too_few_args(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['cmd', '--flag=.+'], returncode=0)
            subprocess.check_call(['cmd'])

    @raises(AssertionError)
    def test_too_many_args(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['cmd', '--flag=.+'], returncode=0)
            subprocess.check_call(['cmd', '--flag=YES', '--unexpected'])

    def test_string_command(self):
        with subprocess_mock.patch_subprocess() as mock:
            mock.expect('just_a_string', returncode=0)
            subprocess.check_call('just_a_string')

    def test_side_effect_stdout(self):
        def side_effect(argv, stdin, stdout, stderr):
            print("OH HI THERE!", file=stdout)
            return 0

        with subprocess_mock.patch_subprocess() as mock:
            mock.expect('foo', side_effect=side_effect)
            assert_equal(subprocess.check_output('foo'), b'OH HI THERE!\n')

    def test_side_effect_returncode(self):
        def side_effect(argv, stdin, stdout, stderr):
            return 17

        with subprocess_mock.patch_subprocess() as mock:
            mock.expect('foo', side_effect=side_effect)
            assert_equal(subprocess.call('foo'), 17)

    @raises(AssertionError)
    def test_side_effect_bad_expectation(self):
        """It is an error to specify both side_effect and stdout, stderr or returncode"""
        def side_effect(argv, stdin, stdout, stderr):
            return 0

        with subprocess_mock.patch_subprocess() as mock:
            mock.expect('foo', side_effect=side_effect, stdout="what?")

    def test_side_effect_argv(self):
        def side_effect(argv, stdin, stdout, stderr):
            print(argv[1], file=stdout)
            return 0

        with subprocess_mock.patch_subprocess() as mock:
            mock.expect(['foo', '--lol'], side_effect=side_effect)
            assert_equal(subprocess.check_output(['foo', '--lol']), b'--lol\n')
