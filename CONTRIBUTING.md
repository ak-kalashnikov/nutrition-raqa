# Contributing to Nutrition RAQA

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Docker (optional)

### Setup Development Environment

```bash
# Clone the repository
git clone <repo-url>
cd Nutrition

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
make install
make install-dev

# Build RAG database
make build-db

# Run tests
make test

# Start development server
make dev
```

## Development Workflow

1. **Create a feature branch**
  ```bash
   git checkout -b feature/your-feature-name
  ```
2. **Make your changes**
  - Write code following the style guide
  - Add tests for new features
  - Update documentation
3. **Test your changes**
  ```bash
   make test
   make lint
  ```
4. **Commit with conventional commits**
  ```bash
   git commit -m "feat: add new retrieval strategy"
   git commit -m "fix: correct FAISS index loading"
   git commit -m "docs: update API documentation"
  ```
5. **Push and create pull request**
  ```bash
   git push origin feature/your-feature-name
  ```

## Code Style

- **Formatter**: Black (line length: 100)
- **Import sorting**: isort
- **Linter**: Ruff

Run formatting and linting:

```bash
make format
make lint
```

### Code Guidelines

1. **Docstrings**: Use Google-style docstrings
2. **Type hints**: Add type hints to all functions
3. **Error handling**: Use try-except with specific exceptions
4. **Logging**: Use structured logging

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_retriever.py -v
```

### Writing Tests

1. Place tests in `tests/` directory
2. Name test files `test_*.py`
3. Use descriptive test names
4. Mock external API calls

## Pull Request Process

1. **Ensure CI passes**
  - All tests pass
  - Linting checks pass
2. **Update documentation**
  - Update README if adding features
  - Add docstrings to new functions
3. **Write descriptive PR description**
  - What does this PR do?
  - Why is it needed?
  - How was it tested?

Thank you for contributing!