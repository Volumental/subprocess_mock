# subprocess_mock
Easy mocking of the `subprocess` python module.

The following will patch the subprocess module so that no new processes are spawned.

    with subprocess_mock.patch_subprocess() as mock:
        mock.expect(['ls', '-l'], returncode=0)
        subprocess.check_call(['ls', '-l'])

## Author
Samuel Carlsson <samuel.carlsson@volumental.com>
