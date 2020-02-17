from google.cloud import secretmanager
import base64
import json
import os
import logging

class Secrets:
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
    def __init__(self,secret,**kwargs):
        logging.getLogger(__name__)
        self.secret = secret

        assert 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ, "This module requires the GOOGLE_APPLICATION_CREDENTIALS environment variable be set"

        supported_project_env_vars = [ 'PROJECT', 'GOOGLE_CLOUD_PROJECT', 'GCP_PROJECT', 'GCLOUD_PROJECT' ]

        self.create_if_not_present = kwargs.get('create_if_not_present',True)
        self.version = kwargs.get('version','latest')
        self.project = kwargs.get('project',None)
        for prj in supported_project_env_vars:
            if self.project:
                break
            self.project = os.environ.get(prj,None)

        assert self.project, "Project must be specified"

        self.client = secretmanager.SecretManagerServiceClient()
        self._secrets = {}
        self._encoded_secrets = {}

        if not self._secret_exists(secret):
            if not self.create_if_not_present:
                raise Exception("Requested secret {} does not exist and you chose not to create it".format(secret))
            logging.info("Creating secret resource")
            self._create_secret_resource(secret)

        self.name = f"projects/{self.project}/secrets/{secret}/versions/{self.version}"
        if self._secret_version_exists(self.name):
            x = self.client.access_secret_version(self.name).payload.data.decode("utf-8")
            self._encoded_secrets = json.loads(x)
            for k,v in self._encoded_secrets.items():
                self._secrets[k] = base64.b64decode(v).decode('ascii')
    @property
    def secrets(self) -> dict:
        return self._secrets
    def __iter__(self):
        return iter(self._secrets.items())
    def _secret_exists(self,name):
        logging.info("checking if secret exists")
        try:
            self.client.get_secret(self.client.secret_path(self.project, name))
            return True
        except:
            return False
    def _secret_version_exists(self,path):
        try:
            x = self.client.access_secret_version(path)
            return True
        except:
            return False
    def _create_secret_resource(self,name):
        try:
            self.client.create_secret(self.client.project_path(self.project), name, { 'replication': { 'automatic': {}}})
        except Exception as e:
            logging.error("Failed to create secret resource: {}".format(e))
    def set(self,key,val):
        """
        The key/val here aren't the key/val of secretmanager, they're a key/val within a given secret val.
        """
        if type(val) != str:
            logging.warn("Warning, value is not a string so serializing as json")
            val = json.dumps(val)
        if key in self._secrets:
            logging.warn("Warning, you are overwriting an existing key")
        self._secrets[key] = val
        self._encoded_secrets[key] = base64.b64encode(bytes(val,'utf-8')).decode('ascii')
        j_blob = json.dumps(self._encoded_secrets).encode('UTF-8')
        resp = self.client.add_secret_version(self.client.secret_path(self.project, self.secret), {'data': j_blob})
        #version = resp.name.split('/')[-1]
        return resp.name
