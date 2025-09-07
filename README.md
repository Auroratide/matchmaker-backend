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
