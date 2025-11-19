# Contributing to InstaAI Studio

Thank you for your interest in contributing! Here's how you can help make InstaAI Studio better.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/instaai-studio/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - System info (OS, Python version, etc.)
   - Error messages/logs

### Suggesting Features

1. Check existing feature requests
2. Create a new issue with:
   - Clear description of the feature
   - Use case and benefits
   - Possible implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Update documentation
6. Commit with clear messages (`git commit -m 'Add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/instaai-studio.git
cd instaai-studio

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest black flake8 mypy

# Run tests
pytest tests/
```

## Code Style

- Follow PEP 8
- Use type hints where possible
- Write docstrings for functions and classes
- Keep functions focused and small
- Add comments for complex logic

```python
def example_function(param: str) -> dict:
    """
    Brief description of what this does

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    # Implementation
    pass
```

## Testing

- Add tests for new features
- Ensure existing tests pass
- Aim for good coverage

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_video_editor.py

# Run with coverage
pytest --cov=src tests/
```

## Areas for Contribution

### High Priority
- [ ] Web UI implementation
- [ ] Additional video effects
- [ ] Performance optimizations
- [ ] Better error handling
- [ ] More comprehensive tests

### Medium Priority
- [ ] Support for more AI models
- [ ] Template system
- [ ] Analytics integration
- [ ] Multi-account management

### Good First Issues
- [ ] Documentation improvements
- [ ] Example workflows
- [ ] Bug fixes
- [ ] UI/UX improvements

## Questions?

Feel free to open an issue or reach out to the maintainers.

Thank you for contributing! 🎉
