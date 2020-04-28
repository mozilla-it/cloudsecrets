import unittest
import unittest.mock as mock
import os

from google.cloud import secretmanager
from cloudsecrets.file import Secrets


class FakeSecret:
    name = "projects/fake-project/secrets/fake-secret/versions/1"


class FakeClient:
    def __init__(self):
        pass

    def project_path(self):
        return "projects/fake-project"

    def secret_path(self, *args):
        return "projects/fake-project/secrets/fake-secret/versions/1"

    @staticmethod
    def get_secret(*args):
        pass

    def create_secret(self):
        pass

    @staticmethod
    def add_secret_version(*args):
        return FakeSecret

    def access_secret_version(self):
        pass


class TestFileLibrary(unittest.TestCase):
    def test_create_secret_version(self):
        s = Secrets("test-secrets.json", create_if_not_present=True)
        assert s.version == "1"
        s.set("FAKE", "SECRET")
        assert dict(s).get("FAKE") == "SECRET"
        assert s.version == "2"
        s.unset("FAKE")
        assert "FAKE" not in dict(s)
        s.update()
        assert s.version == "4"
