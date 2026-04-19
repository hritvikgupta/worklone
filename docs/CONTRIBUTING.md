# Contributing to Worklone

Thank you for considering contributing to Worklone! We welcome contributions of all kinds — bug fixes, new features, documentation improvements, and tool additions.

> License notice: this project is non-commercial research-use only. Contributions remain under the repository license in [../LICENSE](../LICENSE).

---

## How to Contribute

### Reporting Bugs

Before creating a bug report:

- Check the [issue tracker](https://github.com/YOUR_USERNAME/worklone/issues) for existing reports
- Test with the latest version

When submitting a bug report, include:

- **Clear title** and description
- **Steps to reproduce** the issue
- **Expected vs actual** behavior
- **Environment details** (OS, Python version, Node version)
- **Logs or screenshots** if applicable

### Suggesting Features

Open a [Feature Request](https://github.com/YOUR_USERNAME/worklone/issues) with:

- **Clear title** and description
- **Use case** — why this feature would be useful
- **Proposed solution** — how you think it should work (optional)

### Pull Requests

1. Fork the repository
2. Create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes
4. Add tests if applicable
5. Update documentation if needed
6. Commit with clear messages:
   ```bash
   git commit -m "feat: add Salesforce contact creation tool"
   ```
7. Push and open a Pull Request

---

## Development Setup

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/worklone.git
cd worklone
```

### 2. Backend Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run Tests

```bash
pytest scripts/test_full.py
```

---

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints where possible
- Write docstrings for public functions and classes
- Keep functions focused and under 50 lines when possible

### TypeScript/JavaScript

- Use TypeScript for all new code
- Follow the existing ESLint configuration
- Use functional components with hooks for React

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new tool
fix: resolve memory leak in agent loop
docs: update installation guide
test: add tests for workflow engine
refactor: simplify tool registry
```

Types:
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation changes
- `test` — test additions or modifications
- `refactor` — code refactoring
- `style` — formatting, linting
- `chore` — maintenance tasks

---

## Adding a New Tool

Tools are the easiest way to contribute. See [Tools Documentation](docs/TOOLS.md) for details.

Quick steps:

1. Create tool class in `backend/core/tools/integration_tools_v2/`
2. Implement `get_schema()` and `execute()`
3. Register in `backend/core/tools/catalog.py`
4. Add documentation to `docs/TOOLS.md`
5. Write tests

---

## Adding a New Integration

For OAuth-based integrations:

1. Create tool files in `backend/core/tools/integration_tools_v2/`
2. Add OAuth handler in `backend/lib/oauth/`
3. Add credentials to the tool's `requires_credentials` list
4. Update `.env.example` with required variables
5. Document the setup process

---

## Improving Documentation

Documentation improvements are always welcome:

- Fix typos or unclear explanations
- Add examples and code snippets
- Create tutorials for common use cases
- Translate documentation

---

## Review Process

- All PRs require at least one review
- CI checks must pass before merging
- Maintainers may request changes
- Be patient — reviews take time

---

## Community

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/worklone/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/worklone/discussions)

---

## License

By contributing, you agree that your contributions are licensed under the Worklone Non-Commercial Research License v1.0.
