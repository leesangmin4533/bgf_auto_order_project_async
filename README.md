# BGF Retail Order Automation

This project automates login and product ordering for the BGF Retail store site using Playwright.

## Credentials

The scripts read credentials from environment variables. You can either export
them or place them in a `.env` file.

Set the following variables before running any script:

- `BGF_USER_ID` – your login ID
- `BGF_USER_PW` – your login password

Example on Linux/macOS using exports:

```bash
export BGF_USER_ID=your_id
export BGF_USER_PW=your_password
python bgf_order_automation.py
```

Or create a `.env` file in the project directory:

```
BGF_USER_ID=your_id
BGF_USER_PW=your_password
```

The scripts use [python-dotenv](https://pypi.org/project/python-dotenv/) to
load variables from this file automatically.
