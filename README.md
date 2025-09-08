# Matchmaker Backend (real name tbd)

This is a small python codebase for a soon-to-exist app.

## Development

It's python, set up a virtual environment:

```
# Setup
python -m venv .venv

# Start
source .venv/bin/activate

# Install
pip install -r requirements.txt
```

Docker is used only for locally mucking around. In real life, you'll wanna set up a `.env` file with keys to things. Use the `.env.example` file to tell you what's needed.

Useful commands:

```
# Start Docker (fake pinecone, fake llm)
docker compose up

# Initialize the local pinecone db
python -m src.init-local

# Run the script
python -m src.matchmake
```

## Testing

Run unit tests with pytest:

```
python -m pytest -q
```

### Coda integration test (destructive and slow)

There is a module `test/test_coda_integration.py` that performs real upserts and deletions against your configured Coda doc. It is destructive and can take multiple minutes due to API polling. It is skipped by default unless all required env vars are present and you confirm interactively.

Required test env vars (recommended to set in the shell only):

- `CODA_TEST_ADD_P1`, `CODA_TEST_ADD_P2`
- `CODA_TEST_DUP_P1`, `CODA_TEST_DUP_P2`
- `CODA_TEST_SORT_P1`, `CODA_TEST_SORT_P2`
- `CODA_TEST_MULTI_P1`, `CODA_TEST_MULTI_P2`, `CODA_TEST_MULTI_P3`, `CODA_TEST_MULTI_P4`

Before running, double-check that the doc/table/column IDs and test person IDs point to safe, disposable test data. Then run:

When prompted, type `PROCEED` to confirm. In non-interactive sessions (e.g. CI), the test will be skipped.