"""Register/reload the prepared app. Requires an explicitly chosen hosting account."""

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--reload", action="store_true")
args = parser.parse_args()
username = os.environ["PYTHONANYWHERE_USERNAME"]
token = os.environ["PYTHONANYWHERE_API_TOKEN"]
host = os.getenv("PYTHONANYWHERE_HOST", "www.pythonanywhere.com")
if host not in {"www.pythonanywhere.com", "eu.pythonanywhere.com"}:
    raise SystemExit("Unsupported provider host")
if not re.fullmatch(r"[A-Za-z0-9_-]+", username):
    raise SystemExit("Invalid username")
config = json.loads(Path("deploy/pythonanywhere.json").read_text())
domain_suffix = "eu.pythonanywhere.com" if host.startswith("eu.") else "pythonanywhere.com"
config["domain_name"] = username + "." + domain_suffix
config["webapp"]["command"] = config["webapp"]["command"].replace("USERNAME", username)
base = f"https://{host}/api/v1/user/{username}/websites/"
url = base + config["domain_name"] + "/reload" if args.reload else base
data = b"" if args.reload else json.dumps(config).encode()
request = urllib.request.Request(
    url,
    data=data,
    method="POST",
    headers={
        "Authorization": "Token " + token,
        "Content-Type": "application/json",
    },
)
with urllib.request.urlopen(request, timeout=60) as response:
    print("Provider returned", response.status, "for", config["domain_name"])
