import boto3
import base64
import json
import os
import logging

from cloudsecrets import SecretsBase

from botocore.exceptions import ClientError

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
    def __init__(self,secret,**kwargs) -> None:
        super()
        self.secret = secret

        self.create_if_not_present = kwargs.get('create_if_not_present',True)
        self._version = kwargs.get('version',None)
        self._region = kwargs.get('region',None)

        self.session = boto3.session.Session()
        self.client = self.session.client(service_name='secretsmanager')
        self._secrets = {}
        self._encoded_secrets = {}

        self._load_secrets()

    @property
    def _secret_exists(self) -> bool:
        """
        Test if a secret resource exists
        """
        params = dict(SecretId=self.secret)
        if self._version:
            params['VersionId'] = self._version
        try:
            self.client.get_secret_value(**params)
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
            params['VersionId'] = self._version

        try:
            x = self.client.get_secret_value(**params)
        except:
            self._encoded_secrets = {}
            self._secrets = {}
            return
        self._version = x['VersionId']
        payload = x['SecretBinary'].decode("utf-8")
        self._encoded_secrets = json.loads(payload)
        for k,v in self._encoded_secrets.items():
            secrets[k] = base64.b64decode(v).decode('ascii')
        self._secrets = secrets

    def _create_secret_resource(self) -> None:
        """
        Create the secret resource which will hold versions of secrets. A secret resource on its own has no secret data.
        """
        try:
            self.client.create_secret(Name=self.secret,SecretBinary='{}'.encode('UTF-8'))
        except Exception as e:
            logging.error("Failed to create secret resource: {}".format(e))
            raise

    def _list_versions(self) -> list:
        try:
            resp = self.client.list_secret_version_ids(SecretId=self.secret,IncludeDeprecated=True)
            x = [ (x['VersionId'],x['CreatedDate']) for x in resp['Versions'] ]
            x.sort(key = lambda _x: _x[1]) # sorted oldest to newest
            return [ k for k,v in x ]
        except Exception as e:
            logging.error("Failed to list versions: {}".format(e))
            raise

    def update(self) -> None:
        """
        Commit the current state of self._secrets to a new secret version
        """
        j_blob = json.dumps(self._encoded_secrets).encode('UTF-8')
        resp = self.client.update_secret(SecretId=self.secret,SecretBinary=j_blob)
        self._version = resp['VersionId']

