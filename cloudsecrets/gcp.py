from google.cloud import secretmanager
import base64
import json
import os
import logging

from cloudsecrets import SecretsBase

from google.api_core import exceptions

class Secrets(SecretsBase):
    """
    GCP Implementation of Mozilla-IT application secrets

    A secret is a json dictionary of ascii:base64 key:value pairs.

    Upstream Resource:
    projects/{project}/secrets/{secret}/versions/{version}

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

        assert 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ, "This module requires the GOOGLE_APPLICATION_CREDENTIALS environment variable be set"

        supported_project_env_vars = [ 'PROJECT', 'GOOGLE_CLOUD_PROJECT', 'GCP_PROJECT', 'GCLOUD_PROJECT' ]

        self.create_if_not_present = kwargs.get('create_if_not_present',True)
        self._version = kwargs.get('version','latest')
        self._project = kwargs.get('project',None)
        for prj in supported_project_env_vars:
            if self._project:
                break
            self._project = os.environ.get(prj,None)

        assert self._project, "Project must be specified"

        self.client = secretmanager.SecretManagerServiceClient()
        self._secrets = {}
        self._encoded_secrets = {}

        self._load_secrets()

    @property
    def _secret_exists(self) -> bool:
        """
        Test if a secret resource exists
        """
        try:
            self.client.get_secret(self.client.secret_path(self.project, self.secret))
            return True
        except exceptions.NotFound:
            return False
        except:
            raise

    def _load_secrets(self) -> None:
        """
        Load upstream secret resource, replacing local secrets
        """
        secret_path = f"projects/{self._project}/secrets/{self.secret}/versions/{self._version}"
        secrets = {}
        if self.create_if_not_present and not self._secret_exists:
            self._create_secret_resource()

        try:
            x = self.client.access_secret_version(secret_path)
        except:
            self._encoded_secrets = {}
            self._secrets = {}
            return
        self._version = x.name.split('/')[-1]
        payload = x.payload.data.decode("utf-8")
        self._encoded_secrets = json.loads(payload)
        for k,v in self._encoded_secrets.items():
            secrets[k] = base64.b64decode(v).decode('ascii')
        self._secrets = secrets

    def _create_secret_resource(self) -> None:
        """
        Create the secret resource which will hold versions of secrets. A secret resource on its own has no secret data.
        """
        try:
            self.client.create_secret(self.client.project_path(self.project), self.secret, { 'replication': { 'automatic': {}}})
        except Exception as e:
            logging.error("Failed to create secret resource: {}".format(e))
            raise

    def update(self) -> None:
        """
        Commit the current state of self._secrets to a new secret version
        """
        j_blob = json.dumps(self._encoded_secrets).encode('UTF-8')
        resp = self.client.add_secret_version(self.client.secret_path(self.project, self.secret), {'data': j_blob})
        self._version = resp.name.split('/')[-1]
