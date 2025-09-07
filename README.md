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

## Documentation

Please refer to the [Architecture Folder](./architecture/) to get oriented with how thing work! It also includes future considerations.

## Testing

Sorry, I'm relatively new to python so I created a test folder but there's nothing in it right now. We really should test tho~
