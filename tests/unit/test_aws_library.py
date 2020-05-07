import json
import unittest

import boto3
import simplejson
from nose.tools import assert_raises
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
    def test_unset_secrets(self):
        secrets = Secrets(self.secret_name, connection=self.connection)
        secrets.set(self.secret_key, self.secret_value)
        secrets.unset(self.secret_key)
        assert dict(secrets).get(self.secret_key) is None

    @mock_secretsmanager
    def test_delete_secret(self):
        self.connection.create_secret(Name="test-secret", SecretBinary=b("{}"))
        secrets = Secrets("test-secret", connection=self.connection)
        secrets.delete()
        from botocore.exceptions import ClientError

        with assert_raises(ClientError):
            self.connection.get_secret_value(SecretId="test-secret")

    @mock_secretsmanager
    def test_unpack_response_secret_string_empty_string(self):
        secret_id = "test-secret"
        secret_string = ""
        self.connection.create_secret(Name=secret_id, SecretString=secret_string)
        secret_response = self.connection.get_secret_value(SecretId=secret_id)
        with assert_raises(simplejson.errors.JSONDecodeError):
            Secrets.unpack_response(secret_response)

    @mock_secretsmanager
    def test_unpack_response_secret_string_empty_dictionary(self):
        secret_id = "test-secret"
        secret_string = json.dumps(dict())
        self.connection.create_secret(Name=secret_id, SecretString=secret_string)
        secret_response = self.connection.get_secret_value(SecretId=secret_id)
        assert json.loads(secret_string) == Secrets.unpack_response(secret_response)

    @mock_secretsmanager
    def test_unpack_response_secret_string(self):
        secret_id = "test-secret"
        secret_dictionary = {"A": "A", "B": "B"}
        secret_string = json.dumps(secret_dictionary)
        self.connection.create_secret(Name=secret_id, SecretString=secret_string)
        secret_response = self.connection.get_secret_value(SecretId=secret_id)
        assert json.loads(secret_string) == Secrets.unpack_response(secret_response)

    @mock_secretsmanager
    def test_unpack_response_secret_binary(self):
        import base64
        import simplejson as json

        secret_id = "test-secret"
        expected = {"A": "A", "B": "B"}
        binary_secret_dictionary = {}
        for k, v in expected.items():
            binary_secret_dictionary[k] = base64.b64encode(v.encode("ascii"))
        self.connection.create_secret(
            Name=secret_id, SecretBinary=json.dumps(binary_secret_dictionary)
        )
        secret_response = self.connection.get_secret_value(SecretId=secret_id)
        actual = Secrets.unpack_response(secret_response)
        assert expected == actual

    @mock_secretsmanager
    def test__create_secret_resource(self):
        secrets = Secrets(
            "super-secret", connection=self.connection, create_if_not_present=True
        )
        assert secrets.secrets == dict()
