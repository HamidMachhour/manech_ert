# Contributing to ERT Station

Thank you for considering contributing to the ERT Station project! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive to all contributors
- Provide constructive feedback
- Focus on code quality and project goals

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/manech_ert.git
   cd manech_ert
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

```bash
# Run setup script
bash setup.sh

# Start development environment
make dev
```

## Making Changes

### Code Style

- **PHP**: Follow PSR-12 coding standard
  ```bash
  ./vendor/bin/pint  # Auto-format
  ```

- **Python**: Follow PEP 8
  ```bash
  black emulator/
  ```

- **JavaScript**: Use vanilla JS or modern standards
  - No semicolons (optional)
  - 2-space indentation
  - Descriptive variable names

### Database Changes

- Create migration: `php artisan make:migration create_table_name`
- Add rollback logic
- Test with `make migrate` and `make migrate-rollback`

### Adding Features

1. **Create a branch**: `git checkout -b feature/my-feature`
2. **Write code** with tests
3. **Run tests**: `make test`
4. **Lint code**: `make lint`
5. **Commit with clear message**:
   ```bash
   git commit -m "feat: add new feature description"
   ```

### Commit Message Format

Follow Conventional Commits:

```
type(scope): description

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

**Examples**:
```
feat(scans): add real-time data streaming
fix(emulator): correct pseudo-depth calculation
docs(readme): update installation instructions
```

## Testing

### Before Submitting

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Lint code
make lint

# Test Python emulator
make test-emulator
```

### Writing Tests

- Place tests in `tests/` directory
- Use descriptive test names
- Test both success and failure cases
- Example:
  ```php
  public function test_can_create_scan()
  {
      $scan = Scan::factory()->create();
      $this->assertDatabaseHas('scans', ['id' => $scan->id]);
  }
  ```

## Pull Request Process

1. **Update documentation** if needed
2. **Add tests** for new features
3. **Ensure all tests pass**: `make test`
4. **Run linting**: `make lint`
5. **Push to your fork**:
   ```bash
   git push origin feature/my-feature
   ```
6. **Create Pull Request** on GitHub with:
   - Clear title describing changes
   - Reference to related issues (#123)
   - Description of changes
   - Testing instructions (if applicable)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing completed

## Related Issues
Closes #(issue)

## Screenshots (if applicable)
<!-- Add screenshots here -->
```

## Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Create new issue** with:
   - Clear title
   - Detailed description
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots/logs if applicable
   - Environment (OS, PHP version, Python version)

### Bug Report Example

```markdown
## Description
The CSV export is missing the Rho column when filtering by electrode pair.

## Steps to Reproduce
1. Create a scan
2. Filter by Stake A = 1
3. Click "Export to CSV"

## Expected Behavior
CSV should contain all 8 columns including Rho

## Actual Behavior
CSV only has 7 columns, Rho is missing

## Environment
- OS: Ubuntu 22.04
- PHP: 8.3.5
- Browser: Chrome 125
```

## Feature Requests

1. **Describe the use case** - Why do we need this?
2. **Provide examples** - How should it work?
3. **Discuss implementation** - Any ideas on how to build it?

### Feature Request Example

```markdown
## Feature: Real-time Data Visualization

### Problem
Users can't see data patterns until after scan completes.

### Solution
Add WebSocket real-time updates to show matrix points as they're collected.

### Implementation Ideas
- Use Laravel Broadcasting
- WebSocket server (Pusher or Socket.io)
- Update React component as data arrives
```

## Documentation Contributions

- Fork and edit `.md` files directly
- Follow Markdown syntax
- Keep examples updated
- Add your name to CONTRIBUTORS.md

## Project Structure

```
manech_ert/
├── app/                    # Laravel application code
│   ├── Console/            # CLI commands & jobs
│   ├── Http/               # Controllers & middleware
│   └── Models/             # Eloquent models
├── emulator/               # Python hardware emulator
├── resources/views/        # Blade templates
├── routes/                 # Route definitions
├── tests/                  # Test files
├── database/migrations/    # Database schema
└── docs/                   # Documentation
```

## Performance Guidelines

- Write efficient queries (use eager loading)
- Avoid N+1 queries
- Cache expensive operations
- Use pagination for large datasets
- Profile code before optimizing

## Security Guidelines

- Never commit `.env` files
- Sanitize user input
- Use prepared statements
- Validate API requests
- Don't log sensitive data
- Keep dependencies updated

## Submitting Changes

1. Rebase on latest `main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Push to your fork:
   ```bash
   git push origin feature/my-feature
   ```

3. Create Pull Request with clear description

4. Address review feedback:
   ```bash
   git add .
   git commit --amend --no-edit
   git push --force-with-lease
   ```

## Recognition

Contributors will be recognized in:
- README.md CONTRIBUTORS section
- GitHub contributors page
- Release notes

## Questions?

- Open a discussion on GitHub
- Check existing issues/PRs
- Review documentation
- Contact maintainers

---

## Helpful Resources

- [Laravel Documentation](https://laravel.com/docs)
- [PHP PSR-12](https://www.php-fig.org/psr/psr-12/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Workflow](https://git-scm.com/book/en/v2)

Thank you for contributing to ERT Station! 🙏
