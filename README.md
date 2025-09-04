# nmt-fastapi-library

[![codecov](https://codecov.io/github/not-mt/nmt-fastapi-library/branch/main/graph/badge.svg)](https://codecov.io/github/not-mt/nmt-fastapi-library)

**nmtfast** (not-MT for FastAPI) is a Python module designed to provide reusable utilities, middleware, and access control mechanisms for FastAPI-based microservices and web applications.

## Features

- **Access Control (ACLs)**: Fine-grained access rules based on OAuth2 client IDs, API keys, and request parameters.
- **Authentication Helpers**: Support for validating and enforcing authentication using OAuth2 and API keys.
- **Middleware Utilities**: Common middleware for logging, request validation, and security.
- **FastAPI Enhancements**: Helper functions for request handling, response formatting, and more.

## Getting Started

### Prerequisites

- Python 3.12+

### Prepare Development Environment

Clone the repository and install dependencies using Poetry:

```bash
git clone https://github.com/not-mt/nmt-fastapi-library.git
cd nmt-fastapi-library
```

Create a virtual environment and install Poetry:

```bash
test -d .venv || python -m venv .venv
source .venv/Scripts/activate
pip install poetry
cp samples/poetry.toml .
```

Install dependencies:

```bash
poetry install
```

Install pre-commit:

```bash
pre-commit install
```

### OPTIONAL: VS Code (on Windows)

Follow these steps if you are developing on a Windows system and have a bash shell available (most likely from [Git for Windows](https://git-scm.com/downloads/win)).

Copy samples:

```bash
cp -urv samples/{.local,.vscode,*} .
```

These files will be excluded by `.gitignore`, and you may customize however you would like. These are the notable files:

- **.local/activate.env**
  - This file will be sourced in a custom terminal profile (defined in `nmt-fastapi-library.code-workspace` )
  - Customize `PROJECTS` to reflect the root path to your software projects

- **nmt-fastapi-library.code-workspace**
  - Sensible defaults are specified here and may be customized as necessary
  - A `terminal.integrated.defaultProfile.windows` is set to use the `.local/activate.env` file when starting new terminals

**NOTE:** You can update `PROJECTS` in `.local/activate.env` file manually, or you can use this command to update it for you. This will set the value to the parent directory of your current directory:

```bash
# get the parent directory, and replace /c/path with C:/path
rpd=$(dirname "$(pwd)" | sed -E 's|^/([a-z])|\U\1:|')
sed \
  -e 's|# export PROJECTS=".*FIXME.*$|export PROJECTS="'"$rpd"'"|' \
  -i .local/activate.env
```

Test the activate script:

```bash
source .local/activate.env
```

Once files have been customized, you may re-open VS Code using the `nmt-fastapi-library.code-workspace` file.

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2025 Alexander Haye
