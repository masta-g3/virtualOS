# PydanticAI Agents

Experiments with [PydanticAI](https://ai.pydantic.dev/) for building AI agents.

## Setup

```bash
# Install dependencies
uv sync

# Configure API keys in .env
cp .env.example .env  # Then add your keys
```

Required environment variables:
- `OPENAI_API_KEY` - for OpenAI models
- `ANTHROPIC_API_KEY` - for Anthropic models

## Usage

```bash
uv run python virtual_agent.py
```

## Scripts

- `virtual_agent.py` - AI agent with sandboxed virtual filesystem (no real disk access)

## Documentation

See [docs/STRUCTURE.md](docs/STRUCTURE.md) for project architecture.