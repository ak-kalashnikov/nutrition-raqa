# Contributing to Nutrition & Sports Health RAQA

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Be respectful and inclusive. We welcome contributions from everyone regardless of background.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/yourusername/nutrition-raqa/issues)
2. Create a new issue with:
   - **Title:** Short description of the bug
   - **Description:** Step-by-step reproduction
   - **Expected vs Actual:** What should happen vs what happened
   - **Environment:** Python version, OS, Python packages

### Suggesting Features

1. Open a GitHub issue with the `enhancement` label
2. Include:
   - Use case and motivation
   - Proposed implementation (if applicable)
   - Additional context

### Submitting Code

#### Setup Development Environment

```bash
# Clone repo
git clone https://github.com/yourusername/nutrition-raqa.git
cd nutrition-raqa

# Create virtual env
python -m venv .venv
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest black ruff pytest-cov
```

#### Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Follow the code style:
   ```bash
   black app/ tests/
   ruff check app/ tests/ --fix
   ```

3. Write/update tests:
   ```bash
   pytest -v
   ```

4. Commit with clear messages:
   ```bash
   git commit -m "feat: add new retriever model support"
   ```

5. Push and open a Pull Request:
   ```bash
   git push origin feature/my-feature
   ```

#### Pull Request Checklist

- [ ] Code follows project style (black + ruff)
- [ ] Tests pass locally (`pytest -v`)
- [ ] New tests added for new features
- [ ] README updated if needed
- [ ] Commit messages are clear and descriptive
- [ ] No merge conflicts with main branch

## Code Style

This project uses:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting

```bash
# Auto-format
black app/ tests/

# Lint (auto-fix where possible)
ruff check app/ tests/ --fix
```

## Testing

All pull requests require passing tests:

```bash
# Run all tests
pytest -v

# Run tests with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_retriever.py -v
```

### Writing Tests

- Use `pytest` framework
- Place tests in `tests/` directory
- Follow naming: `test_*.py` files, `test_*` functions
- Use fixtures for setup/teardown

Example:
```python
def test_retriever_loads_documents(sample_data_file):
    """Test that retriever correctly loads documents."""
    ret = Retriever()
    ret.load_documents(sample_data_file)
    assert len(ret.docs) == 3
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to functions and classes (Google style)
- Comment complex logic

## Project Structure

```
nutrition-raqa/
├── app/              # Main application code
├── tests/            # Test suite
├── data/             # Sample data (JSONL)
├── demo.py           # Streamlit demo
├── Dockerfile        # Container config
├── requirements.txt  # Dependencies
└── README.md         # Documentation
```

## Questions?

Open a GitHub discussion or issue. Maintainers will respond as soon as possible.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for making this project better! 🙏
