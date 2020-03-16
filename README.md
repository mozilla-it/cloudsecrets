# cloudsecrets

cloudsecrets is a thin layer for cloud vendor secrets managers which asserts some consistency between various solutions and makes implementing multi-cloud friendly code easy.

The cloudsecrets library includes a cli cloud-secrets which exposes all the features of the library.

Current supported platforms include GCP (secretmanager) and AWS (secrets manager).

## How to Install

From the command line:
```
pip3 install git+https://github.com/mozilla-it/cloudsecrets.git
```
From Pipenv:
```
[packages]
cloudsecrets = { version = "*", git = "https://github.com/mozilla-it/cloudsecrets.git", ref = "master", editable = false }
```
If you're using pipenv to generate a requirements file for pypi try this syntax:
```
pipenv install
pipenv run pip freeze | grep -v pkg-resources | sed -e 's|^-e ||g' -e 's|\(.*\)egg=\(.*\)|\2@\1egg=\2|g' > requirements.txt
pip3 install --upgrade --no-cache-dir .
```

## How to Use the library

For AWS and GCP the library assumes you're fully authenticated and authorized for secrets management. For GCP, you will need to let the library know what project you want to use. This can be done with the PROJECT env var or by passing the `project` argument to the class.

```
>>> from cloudsecrets.gcp import Secrets
>>> mySecrets = Secrets("afrank-secrets")
>>> dict(mySecrets)
{'THIS': 'is a secret', 'ANOTHER': 'SECRET2'}
>>> mySecrets.set('another','secret')
'projects/357203911999/secrets/afrank-secrets/versions/5'
>>> dict(mySecrets)
{'THIS': 'is a secret', 'ANOTHER': 'SECRET2', 'another': 'secret'}

```
Switching between versions
```
>>> s = Secrets("afrank-secrets",version="latest",project="dp2-stage")
>>> dict(s)
{'THIS': 'is a secret', 'ANOTHER': 'SECRET2', 'another': 'secret', 'YETANOTHER': 'SECRETVALUE'}
>>> s.set('THIS','is a different secret')
WARNING:root:Warning, you are overwriting an existing key
'projects/357203911999/secrets/afrank-secrets/versions/7'
>>> s = Secrets("afrank-secrets",version=6,project="dp2-stage")
>>> dict(s).get('THIS')
'is a secret'
>>> s = Secrets("afrank-secrets",version="latest",project="dp2-stage")
>>> dict(s).get('THIS')
'is a different secret'
```
Rollback to an old version, then set that version to latest
```
>>> dict(s)
{'THIS': 'is a different secret', 'ANOTHER': 'SECRET2', 'another': 'secret', 'YETANOTHER': 'SECRETVALUE', 'key': 'val'}
>>> s.version
'8'
>>> s.rollback()
>>> s.version
'7'
>>> dict(s)
{'THIS': 'is a different secret', 'ANOTHER': 'SECRET2', 'another': 'secret', 'YETANOTHER': 'SECRETVALUE'}
>>> s.update()
'projects/357203911999/secrets/afrank-secrets/versions/9'
>>> dict(s)
{'THIS': 'is a different secret', 'ANOTHER': 'SECRET2', 'another': 'secret', 'YETANOTHER': 'SECRETVALUE'}
```

## How to Use the CLI

```
usage: cloud-secrets [-h] [-E] [-D] [-X] [-p PROVIDER] -s SECRET [-k KEY]
                       [-f FILE] [-v VALUE] [-b B64VALUE] [-g GCPPROJECT]

Mozilla-IT Secrets

optional arguments:
  -h, --help            show this help message and exit
  -E, --encrypt         Encrypt. Cannot be used with -D or -X
  -D, --decrypt         Decrypt. Cannot be used with -E or -X
  -X, --delete          Delete Secret (or key if -k is specified). Cannot be
                        used with -E or -D
  -p PROVIDER, --provider PROVIDER
                        Provider. Supported: aws|gcp
  -s SECRET, --secret SECRET
                        which secret resource to work with
  -k KEY, --key KEY     which key inside a secret to work with. if no key is
                        specified you are working on the whole secret
  -f FILE, --file FILE  file to use for input {encryption} or output
                        {decryption}
  -v VALUE, --value VALUE
                        value to use for input {encryption}. Note: this
                        argument takes precedence over -f
  -b B64VALUE, --b64value B64VALUE
                        base64-encoded value to use for input {encryption}.
                        Note: this argument takes precedence over -v
  -g GCPPROJECT, --gcpproject GCPPROJECT
                        if using the GCP secret manager you must specify the
                        project you want to use
```
Create and retrieve a secret key:
```
$ cloud-secrets -E -p GCP -g dp2-stage -s afrank-secrets -k YETANOTHER -v SECRETVALUE

$ cloud-secrets -D -p GCP -g dp2-stage -s afrank-secrets -k YETANOTHER
SECRETVALUE
```
