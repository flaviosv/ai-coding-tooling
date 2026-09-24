import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import detect_remote as dr

GITHUB = {"platform": "github", "host": "github.com", "owner": "octocat", "repo": "hello-world"}
ADO = {"platform": "ado", "host": "dev.azure.com", "org": "fabrikam", "project": "Fiber Web", "repo": "web"}


class DetectTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(dr, "resolve_ssh_alias", side_effect=lambda host: host)
        self.alias = patcher.start()
        self.addCleanup(patcher.stop)

    def test_github_https(self):
        self.assertEqual(dr.detect("https://github.com/octocat/hello-world.git"), GITHUB)

    def test_github_scp(self):
        self.assertEqual(dr.detect("git@github.com:octocat/hello-world.git"), GITHUB)

    def test_github_ssh_alias_is_resolved(self):
        self.alias.side_effect = lambda host: "github.com" if host == "github-personal.com" else host
        self.assertEqual(dr.detect("git@github-personal.com:octocat/hello-world.git"), GITHUB)

    def test_ado_https_with_user_and_encoded_project(self):
        url = "https://fabrikam@dev.azure.com/fabrikam/Fiber%20Web/_git/web"
        self.assertEqual(dr.detect(url), ADO)

    def test_ado_ssh(self):
        self.assertEqual(dr.detect("git@ssh.dev.azure.com:v3/fabrikam/Fiber%20Web/web"), ADO)

    def test_ado_legacy_https(self):
        self.assertEqual(dr.detect("https://fabrikam.visualstudio.com/Fiber%20Web/_git/web"), ADO)

    def test_ado_legacy_default_collection(self):
        url = "https://fabrikam.visualstudio.com/DefaultCollection/Fiber%20Web/_git/web"
        self.assertEqual(dr.detect(url), ADO)

    def test_ado_legacy_ssh(self):
        url = "fabrikam@vs-ssh.visualstudio.com:v3/fabrikam/Fiber%20Web/web"
        self.assertEqual(dr.detect(url), ADO)

    def test_on_prem_server_is_unsupported(self):
        self.assertIsNone(dr.detect("https://tfs.example.com/tfs/Coll/Proj/_git/web"))

    def test_https_host_is_never_alias_resolved(self):
        dr.detect("https://gitlab.com/a/b.git")
        self.alias.assert_not_called()


class ResolveSshAliasTest(unittest.TestCase):
    def test_reads_hostname_from_ssh_g(self):
        proc = mock.Mock(returncode=0, stdout="user git\nhostname github.com\nport 22\n")
        with mock.patch.object(dr.subprocess, "run", return_value=proc):
            self.assertEqual(dr.resolve_ssh_alias("github-personal.com"), "github.com")

    def test_falls_back_to_host_on_failure(self):
        with mock.patch.object(dr.subprocess, "run", side_effect=OSError):
            self.assertEqual(dr.resolve_ssh_alias("x"), "x")


if __name__ == "__main__":
    unittest.main()
