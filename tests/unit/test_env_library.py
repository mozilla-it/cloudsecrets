import unittest
import unittest.mock as mock
import os

from cloudsecrets.env import Secrets


class TestEnvLibrary(unittest.TestCase):
    def test_create_secret_version(self):
        s = Secrets("")
        ver = s.version
        s.set("FAKE", "SECRET")
        assert dict(s).get("FAKE") == "SECRET"
        assert s.version == str(int(ver) + 1)
        s.unset("FAKE")
        assert "FAKE" not in dict(s)
        s.update()
        assert s.version == str(int(ver) + 3)
