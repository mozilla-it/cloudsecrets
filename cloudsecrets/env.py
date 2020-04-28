from cloudsecrets import SecretsBase
import base64
import json
import os
import logging


class Secrets(SecretsBase):
    def __init__(self, secret=None, **kwargs) -> None:
        super().__init__(secret, **kwargs)
        self._version = "1"
        self._load_secrets()

    def _load_secrets(self) -> None:
        for k, v in os.environ.items():
            self.set(k, v)

    def update(self) -> None:
        self._version = str(int(self._version) + 1)
