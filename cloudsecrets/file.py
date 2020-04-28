from cloudsecrets import SecretsBase
import os
import json


class Secrets(SecretsBase):
    def __init__(self, filename, **kwargs) -> None:
        super().__init__("", **kwargs)
        self.filename = filename
        self.create_if_not_present = kwargs.get("create_if_not_present", True)
        self._version = "1"
        self._load_secrets()

    def _load_secrets(self) -> None:
        if not os.path.exists(self.filename) and self.create_if_not_present:
            f = open(self.filename, "w")
            f.write("{}")
            f.close()
        j_blob = open(self.filename).read()
        d = json.loads(j_blob)
        for k, v in d.items():
            self.set(k, v)

    def update(self) -> None:
        """
        write secret state back to the file
        """
        j_blob = json.dumps(self._encoded_secrets)
        f = open(self.filename, "w")
        f.write(j_blob)
        f.close()
        self._version = str(int(self._version) + 1)
