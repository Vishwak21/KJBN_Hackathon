# Deploy Harvest Ledger on Vishwak's PythonAnywhere account

Account dashboard: https://www.pythonanywhere.com/user/Vishwak/

These steps have not yet been run on the account.

1. Open Files and upload deployment-bundle.zip into /home/Vishwak/.
2. Open Account > API token and create a token if none exists. Keep it on PythonAnywhere; the pa command can discover it inside your account's console.
3. Open Consoles > Bash and paste this block:

```bash
set -e
mkdir -p /home/Vishwak/harvest-ledger
cd /home/Vishwak/harvest-ledger
unzip -o /home/Vishwak/deployment-bundle.zip
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -m pip install --upgrade pythonanywhere
.venv/bin/pa website create --domain Vishwak.pythonanywhere.com --command '/bin/bash /home/Vishwak/harvest-ledger/scripts/pythonanywhere-start.sh'
```

If a command fails, stop and share its error output (without credentials). If python3.12 is unavailable, share that message before choosing another interpreter.

Expected public URLs, only after successful creation:
- https://vishwak.pythonanywhere.com/
- https://vishwak.pythonanywhere.com/health
- https://vishwak.pythonanywhere.com/docs

For an existing app created using this configuration, reload after uploading an updated package:
```bash
cd /home/Vishwak/harvest-ledger
.venv/bin/pa website reload --domain Vishwak.pythonanywhere.com
```

Official references:
- https://help.pythonanywhere.com/pages/ASGICommandLine/
- https://help.pythonanywhere.com/pages/GettingYourAPIToken/

Public deployment, account compatibility and review-period availability remain unverified until the account-side commands succeed.
