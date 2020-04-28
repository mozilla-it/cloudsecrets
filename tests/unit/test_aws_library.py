import unittest

import boto3
from six import b

from cloudsecrets.aws import Secrets


class TestAWSLibrary(unittest.TestCase):
    from moto import mock_secretsmanager

    @classmethod
    def setUpClass(self):
        self.secret_name = "FAKE_SECRET_NAME"
        self.secret_key = "FAKE"
        self.secret_value = "SECRET"
        self.connection = boto3.client("secretsmanager", region_name="us-east-1")

    @mock_secretsmanager
    def test_create_secret(self):
        secrets = Secrets(self.secret_name, connection=self.connection)
        secrets.set(self.secret_key, self.secret_value)
        assert dict(secrets).get(self.secret_key) == self.secret_value

    @mock_secretsmanager
    def test_list_secrets(self):
        secrets = Secrets(self.secret_name, connection=self.connection)
        secrets.set(self.secret_key, self.secret_value)
        secrets.unset(self.secret_key)
        assert dict(secrets).get(self.secret_key) is None

    @mock_secretsmanager
    def test_delete_secret(self):
        from nose.tools import assert_raises

        self.connection.create_secret(Name="test-secret", SecretBinary=b("{}"))
        secrets = Secrets("test-secret", connection=self.connection)
        secrets.delete("test-secret")
        from botocore.exceptions import ClientError

        with assert_raises(ClientError):
            self.connection.get_secret_value(SecretId="test-secret")
