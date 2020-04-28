import boto3
import base64
import json
import os
import logging

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
        logging.debug(f"AWS {self.__init__.__name__}({secret, region})")
        super().__init__(secret, **kwargs)
        if connection is None:
            self.connection = boto3.client("secretsmanager", region_name=region)
        else:
            self.connection = connection
        self._init_secrets()

    def update(self) -> None:
        logging.debug(f"AWS {self.update.__name__}({self.secret})")
        secret_json_blob = b(json.dumps(self._encoded_secrets))
        if self._secret_exists:
            logging.debug(
                f"AWS {self.update.__name__}({self.secret}), updating an existing value"
            )
            secret = self.connection.put_secret_value(
                SecretId=self.secret, SecretBinary=secret_json_blob
            )
        else:
            logging.debug(
                f"AWS {self.update.__name__}({self.secret}), creating a new secret"
            )
            secret = self.connection.create_secret(
                Name=self.secret, SecretBinary=secret_json_blob
            )
        self._version = secret["VersionId"]

    def delete(self, key) -> None:
        self.connection.delete_secret(SecretId=key)

    @property
    def _secret_exists(self) -> bool:
        """
        Test if a secret resource exists
        """
        try:
            self.connection.get_secret_value(SecretId=self.secret)
            return True
        except:
            return False

    def _load_secrets(self) -> None:
        """
        Load upstream secret resource, replacing local secrets
        """
        secrets = {}
        if self.create_if_not_present and not self._secret_exists:
            self._create_secret_resource()

        params = dict(SecretId=self.secret)
        if self._version:
            params["VersionId"] = self._version

        try:
            x = self.connection.get_secret_value(**params)
        except:
            self._encoded_secrets = {}
            self._secrets = {}
            return
        self._version = x["VersionId"]
        payload = x["SecretBinary"]
        self._encoded_secrets = json.loads(payload)
        for k, v in self._encoded_secrets.items():
            secrets[k] = base64.b64decode(v).decode("ascii")
        self._secrets = secrets

    def _create_secret_resource(self) -> None:
        """
        Create the secret resource which will hold versions of secrets. A secret resource on its own has no secret data.
        """
        try:
            self.connection.create_secret(
                Name=self.secret, SecretBinary="{}".encode("UTF-8")
            )
        except Exception as e:
            logging.error("Failed to create secret resource: {}".format(e))
            raise

    def _list_versions(self) -> list:
        try:
            resp = self.connection.list_secret_version_ids(
                SecretId=self.secret, IncludeDeprecated=True, MaxResults=100
            )
            x = [(x["VersionId"], x["CreatedDate"]) for x in resp["Versions"]]
            x.sort(key=lambda _x: _x[1])  # sorted oldest to newest
            return [k for k, v in x]
        except Exception as e:
            logging.error("Failed to list versions: {}".format(e))
            raise
