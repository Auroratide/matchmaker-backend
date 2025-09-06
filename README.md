Codebase for initting Matchmaker doohickers.

## Virtual Environment

```
# Setup
python -m venv .venv

# Start
source .venv/bin/activate
```

## Init Pinecone database

DO NOT RUN THIS PLEASE.

```
python src/init-pinecone.py
```

## Init LOCAL Pinecone database for testing

Do run this tho.

```
python src/init-local.py
```

## Run something

```
python -m src.matchmake
```