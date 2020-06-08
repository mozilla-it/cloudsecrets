import base64
import json
import logging
import os
import threading


class SecretsBase:
    def __init__(self, secret, **kwargs) -> None:
        logging.getLogger(__name__)
        self._secrets = {}
        self._encoded_secrets = {}
        self._timer = None
        self.secret = secret
        self.create_if_not_present = kwargs.get("create_if_not_present", True)
        self._version = kwargs.get("version", None)
        self._polling_interval = kwargs.get("polling_interval", 0)

        assert (
            self._polling_interval <= 0 or not self._version
        ), "Cannot use a non-latest secret version with polling"

    def __del__(self):
        self._timer = None

    @property
    def secrets(self) -> dict:
        return self._secrets

    @property
    def version(self) -> str:
        return self._version

    @property
    def project(self) -> str:
        return self._project

    @property
    def _secret_exists(self) -> bool:
        return True

    def __iter__(self) -> iter:
        return iter(self._secrets.items())

    def _init_secrets(self) -> None:
        if self._polling_interval > 0:
            self._poll_secrets()
        else:
            self._load_secrets()

    def get(self,*args,**kwargs):
        return dict(self).get(*args,**kwargs)

    def _keys(self):
        return dict(self).keys()

    def _list_versions(self) -> list:
        return [self._version]

    def _load_latest(self) -> None:
        self._version = str(self._list_versions()[-1])
        self._load_secrets()

    def _load_secrets(self) -> None:
        self._version = "1"

    def _create_secret_resource(self) -> None:
        pass

    def update(self) -> None:
        pass

    def _poll_secrets(self):
        self._load_latest()
        if self._polling_interval > 0:
            self._timer = threading.Timer(self._polling_interval, self._poll_secrets)
            self._timer.daemon = True
            self._timer.start()

    def set(self, key, val) -> None:
        """
        The key/val here aren't the key/val of secretmanager, they're a key/val within a given secret val.
        """
        if type(val) != str:
            logging.warning("Warning, value is not a string so serializing as json")
            val = json.dumps(val)
        if key in self._secrets:
            logging.warning("Warning, you are overwriting an existing key")
        self._secrets[key] = val
        self._encoded_secrets[key] = base64.b64encode(bytes(val, "utf-8")).decode(
            "ascii"
        )
        self.update()

    def unset(self, key) -> None:
        """
        Unset (delete) a secret key
        """
        if key in self._secrets:
            del self._secrets[key]
        if key in self._encoded_secrets:
            del self._encoded_secrets[key]
        self.update()

    def rollback(self, version="-1") -> None:
        try:
            ver = int(version)
            all_versions = self._list_versions()
            cur_idx = all_versions.index(self._version)
            if ver <= 0:
                self._version = all_versions[cur_idx + ver]
            else:
                self._version = all_versions[ver]
        except:
            # what was provided wasn't a number, so just attempt to use it.
            self._version = version
        self._load_secrets()

    def delete(self) -> None:
        pass
