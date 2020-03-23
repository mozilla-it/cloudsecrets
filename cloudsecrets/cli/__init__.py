#!/usr/bin/python3

import argparse
import os
import logging
import base64
import importlib
import json
import sys

"""
A secret is a json dictionary of ascii:base64 key:value pairs.
"""

PROVIDERS = [ "gcp", "aws" ]

def main():
  parser = argparse.ArgumentParser(description="Mozilla-IT Secrets")
  parser.add_argument('-E','--encrypt',action='store_true', help='Encrypt. Cannot be used with -D or -X')
  parser.add_argument('-D','--decrypt',action='store_true', help='Decrypt. Cannot be used with -E or -X')
  parser.add_argument('-X','--delete', action='store_true', help='Delete Secret (or key if -k is specified). Cannot be used with -E or -D')
  parser.add_argument('-p','--provider',help=f'What upstream provider to use (case insensitive)', type=str.lower, choices=PROVIDERS, default=PROVIDERS[0])
  parser.add_argument('-s','--secret',help='which secret resource to work with', required=True)
  parser.add_argument('-k','--key',help='which key inside a secret to work with. if no key is specified you are working on the whole secret',default=None)
  parser.add_argument('-f','--file',help='file to use for input {encryption} or output {decryption}')
  parser.add_argument('-v','--value',help='value to use for input {encryption}. Note: this argument takes precedence over -f')
  parser.add_argument('-b','--b64value',help='base64-encoded value to use for input {encryption}. Note: this argument takes precedence over -v')
  parser.add_argument('-g','--gcpproject',help='if using the GCP secret manager you must specify the project you want to use',default=None)
  args = parser.parse_args()

  params = {}

  if args.gcpproject:
    params['project'] = args.gcpproject

  try:
    module = importlib.import_module(f'.{args.provider}','cloudsecrets')
    Secrets = getattr(module,'Secrets')
  except:
    raise Exception('Failed to import vendor library. Must provide a valid provider. Supported: GCP|AWS')

  s = Secrets(args.secret,**params)

  if args.delete and args.key:
    s.unset(args.key)
  elif args.delete:
    # delete an entire secret
    raise NotImplementedError

  if args.encrypt and args.key:
    # add or update a key within a secret
    if args.b64value:
      val = base64.b64decode(args.b64value).decode('ascii')
    elif args.value:
      val = args.value
    elif args.file:
      val = open(os.path.expanduser(args.file)).read()
    else:
      raise Exception("Must provide an encryption input value. b64value|value|file")
    s.set(args.key,val)
  elif args.encrypt:
    # add or replace and entire secret
    raise NotImplementedError

  if args.decrypt:
    if args.key:
      x = dict(s)[args.key]
    else:
      x = dict(s)
    if type(x) != str:
      x = json.dumps(x)
    if args.file:
      with open(os.path.expanduser(args.file),'w') as w:
        w.write(x)
    else:
      print(x)

if __name__ == "__main__":
    sys.exit(main())
