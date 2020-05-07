import base64
import logging
import os

import boto3
import simplejson as json
from six import b

from cloudsecrets import SecretsBase


class Secrets(SecretsBase):
    """
    AWS Implementation of Mozilla-IT application secrets

    A secret is a json dictionary of ascii:base64 key:value pairs.

    Upstream Resource:
    regions/{region}/secrets/{secret}/versions/{version}

    By default, "latest" version is used.

    Value (json string):
    {
      "MYSECRET": "VkFMVUU=",
      "creds.json": "ewogICAgImJsb2IiOiAiaGVyZSBpcyBzb21lIHN0dWZmIgp9Cg=="
    }

    Project must be specified, either as a keyword argument or env var.
    Supported env vars are PROJECT, GOOGLE_CLOUD_PROJECT, GCP_PROJECT, GCLOUD_PROJECT
    >>> os.environ['PROJECT'] = "my-project"

    If a secret is specified which does not exist, one will be created unless
    create_if_not_present is set to False
    >>> s = Secrets("my-secrets")

    >>> s = Secrets("non-existent-secrets",create_if_not_present=False)
    Exception: Requested secret non-existent-secrets does not exist and you chose not to create it

    The Secrets class supports being called as a dictionary
    >>> dict(s).get("MYSECRET")
    'VALUE'

    """

    def __init__(self, secret, connection=None, region=None, **kwargs) -> None:
        logging.debug(f"AWS __init__ ({secret, region})")
        super().__init__(secret, **kwargs)
        self.is_binary = kwargs.get("is_binary", True)
        if connection is None:
            self.connection = boto3.client("secretsmanager", region_name=region)
        else:
            self.connection = connection
        self._init_secrets()

    def __del__(self):
        self._secrets = {}
        self._encoded_secrets = {}
        self._timer = None
        self.secret = None

    def update(self) -> None:
        """
        Upsert a secret to AWS SecretsManager.
        """
        logging.debug(f"AWS update ({self.secret})")
        secret_json_blob = b(json.dumps(self._encoded_secrets))
        if self._secret_exists:
            logging.debug(f"AWS update({self.secret}), updating an existing value")
            if self.is_binary:
                secret = self.connection.put_secret_value(
                    SecretId=self.secret, SecretBinary=secret_json_blob
                )
            else:
                secret = self.connection.put_secret_value(
                    SecretId=self.secret, SecretString=secret_json_blob
                )
        else:
            logging.debug(f"AWS update ({self.secret}), creating a new secret")
            if self.is_binary:
                secret = self.connection.create_secret(
                    Name=self.secret, SecretBinary=secret_json_blob
                )
            else:
                secret = self.connection.create_secret(
                    Name=self.secret, SecretString=secret_json_blob
                )
        self._version = secret["VersionId"]

    def delete(self) -> None:
        """
        Delete a secret from AWS SecretsManager.
        """
        logging.debug(f"AWS delete")
        self.connection.delete_secret(SecretId=self.secret)

    @property
    def _secret_exists(self) -> bool:
        """
        Test if a secret resource exists
        """
        logging.debug(f"AWS _secret_exists")
        try:
            self.connection.get_secret_value(SecretId=self.secret)
            return True
        except:
            return False

    def _load_secrets(self) -> None:
        """
        Load upstream secret resource, replacing local secrets
        """
        logging.debug(f"AWS _load_secrets")
        secrets = {}
        if self.create_if_not_present and not self._secret_exists:
            self._create_secret_resource()
        try:
            if self._version:
                x = self.connection.get_secret_value(
                    SecretId=self.secret, VersionId=self._version,
                )
            else:
                x = self.connection.get_secret_value(SecretId=self.secret)
        except:
            self._encoded_secrets = {}
            self._secrets = {}
            return
        kind = Secrets.unpack_response(x)
        self._version = x["VersionId"]
        if self.is_binary:
            payload = x["SecretBinary"]
            self._encoded_secrets = json.loads(payload)
            for k, v in self._encoded_secrets.items():
                secrets[k] = base64.b64decode(v).decode("ascii")
            self._secrets = secrets
        else:
            payload = x["SecretString"]
            self._secrets = json.loads(payload)

    def _create_secret_resource(self) -> None:
        """
        Create the secret resource which will hold versions of secrets. A secret resource on its own has no secret data.
        """
        logging.debug(f"AWS _create_secret_resource")
        try:
            if self.is_binary:
                self.connection.create_secret(
                    Name=self.secret, SecretBinary="{}".encode("UTF-8")
                )
            else:
                self.connection.create_secret(
                    Name=self.secret, SecretString=str(dict())
                )
        except Exception as e:
            logging.error(f"Failed to create secret resource: {e}")
            raise

    def _list_versions(self) -> list:
        logging.debug(f"AWS _list_versions")
        try:
            resp = self.connection.list_secret_version_ids(
                SecretId=self.secret, IncludeDeprecated=True, MaxResults=100
            )
            x = [(x["VersionId"], x["CreatedDate"]) for x in resp["Versions"]]
            x.sort(key=lambda _x: _x[1])  # sorted oldest to newest
            return [k for k, v in x]
        except Exception as e:
            logging.error(f"Failed to list versions: {e}")
            raise

    @staticmethod
    def unpack_response(response):
        if "SecretString" in response:
            secret = response["SecretString"]
            secrets = json.loads(secret)
            return secrets
        else:
            payload = response["SecretBinary"]
            binary_payload = json.loads(payload)
            secrets = {}
            for k, v in binary_payload.items():
                secrets[k] = base64.b64decode(v).decode("UTF-8")
            return secrets
