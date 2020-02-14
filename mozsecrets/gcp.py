from google.cloud import secretmanager
import base64
import json
import os
import logging

"""
Anatomy of a mozsecret:

Secrets are stored upstream in key/value pairs.

The key consists of the project, the secret version and secret name unique to that project.
The value contains a json blob.
  * When the json blob in the value is deserialized it's a dictionary consisting of unique string keys with base64-encoded values.
  * What's contained within the base64-encoded value is at the discretion of the developer.

"""

class Secrets:
    """
    GCP Implementation of Mozilla-IT application secrets
    """
    def __init__(self,secret,**kwargs):
        logging.getLogger(__name__)
        self.version = "latest"
        self.create_if_not_present = True
        self.secret = secret
        if 'version' in kwargs:
            self.version = kwargs['version']
        if 'create_if_not_present' in kwargs:
            self.create_if_not_present = kwargs['create_if_not_present']
        if 'project' in kwargs:
            self.project = kwargs['project']
        else:
            self.project = os.environ.get('PROJECT', None)

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
