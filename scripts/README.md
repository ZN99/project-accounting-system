# Development Scripts

This directory contains utility scripts to streamline development workflow and prevent repeated work when continuing from a fresh context window.

## Available Scripts

### 🚀 init.sh - Initial Setup
First-time setup script for new developers or fresh environments.

**Usage:**
```bash
./scripts/init.sh
```

**What it does:**
- Checks Python version
- Installs dependencies from requirements.txt
- Creates necessary directories (media/, staticfiles/)
- Runs database migrations
- Collects static files
- Optionally creates superuser

**When to use:**
- First time setting up the project
- After cloning the repository
- After major dependency updates

---

### 🏃 start.sh - Start Development Server
Gracefully starts the Django development server with health checks.

**Usage:**
```bash
./scripts/start.sh              # Start on default port 8000
./scripts/start.sh 8080         # Start on custom port
```

**What it does:**
- Kills existing servers on the port
- Checks for pending migrations
- Collects static files
- Starts Django development server
- Displays access URLs

**When to use:**
- Every time you start working
- After pulling code changes
- When the server crashes

---

### 🧪 test.sh - Run Test Suite
Runs Django tests with various options.

**Usage:**
```bash
./scripts/test.sh                # Run all tests
./scripts/test.sh order          # Run order_management tests
./scripts/test.sh subcontract    # Run subcontract_management tests
./scripts/test.sh quick          # Quick run (verbosity 1)
./scripts/test.sh coverage       # Run with coverage report
./scripts/test.sh order_management.tests.TestProjectModel  # Specific test
```

**What it does:**
- Runs Django test suite
- Supports verbosity levels
- Can generate coverage reports (if coverage installed)
- Returns proper exit codes for CI/CD

**When to use:**
- Before committing code
- After implementing features
- In CI/CD pipelines
- When debugging test failures

---

### 🔍 lint.sh - Code Quality Checks
Runs linters and code quality tools.

**Usage:**
```bash
./scripts/lint.sh
```

**What it does:**
- Django system check (`manage.py check`)
- Flake8 (Python style checker)
- Pylint (code analysis)
- Black (code formatter check)
- Isort (import sorting check)
- Bandit (security checks)
- Autoflake (unused import detection)

**When to use:**
- Before committing code
- During code review
- Before pull requests
- In CI/CD pipelines

**Required packages:**
```bash
pip install flake8 pylint black isort bandit autoflake
```

---

### 🔄 reset.sh - Reset Environment
Resets the development environment to clean state.

**Usage:**
```bash
./scripts/reset.sh
```

**What it does:**
- Kills all running servers
- Removes staticfiles/
- Removes __pycache__ directories
- Removes .pyc files
- Removes test cache
- Optionally resets database (with confirmation)
- Recollects static files

**When to use:**
- When environment is corrupted
- After major code changes
- When troubleshooting weird issues
- Before starting fresh

**⚠️ Warning:** Database reset will delete all data!

---

### 📊 status.sh - System Status
Checks the current state of the development environment.

**Usage:**
```bash
./scripts/status.sh
```

**What it shows:**
- Server status (running/stopped, PID)
- Python version
- Django version
- Database status and size
- Migration status (applied/pending)
- Static files status
- Media directory status
- Dependencies status
- Django system check results

**When to use:**
- After pulling code changes
- When troubleshooting issues
- Before starting work
- To verify environment health

---

## Quick Start Guide

### First Time Setup
```bash
# 1. Make scripts executable
chmod +x scripts/*.sh

# 2. Run initial setup
./scripts/init.sh

# 3. Check status
./scripts/status.sh

# 4. Start server
./scripts/start.sh
```

### Daily Workflow
```bash
# Morning: Check status and start
./scripts/status.sh
./scripts/start.sh

# During development: Run tests
./scripts/test.sh

# Before commit: Lint and test
./scripts/lint.sh
./scripts/test.sh

# Troubleshooting: Reset if needed
./scripts/reset.sh
```

### CI/CD Pipeline
```bash
# Run in CI/CD
./scripts/test.sh coverage
./scripts/lint.sh
```

---

## Script Conventions

### Exit Codes
All scripts follow standard exit code conventions:
- `0` - Success
- `1` - Error or failure

### Colors
Scripts use colored output for clarity:
- 🟢 **Green** - Success messages
- 🔵 **Blue** - Informational messages
- 🟡 **Yellow** - Warnings
- 🔴 **Red** - Errors

### Error Handling
All scripts use `set -e` to exit on error, ensuring failures are caught early.

---

## Troubleshooting

### Permission Denied
If you get "Permission denied" errors:
```bash
chmod +x scripts/*.sh
```

### Port Already in Use
If port 8000 is in use:
```bash
# Kill manually
lsof -ti:8000 | xargs kill -9

# Or use reset script
./scripts/reset.sh
```

### Missing Dependencies
If linters fail in lint.sh:
```bash
pip install flake8 pylint black isort bandit autoflake
```

### Database Issues
If database is corrupted:
```bash
./scripts/reset.sh
# Choose "yes" when asked about database reset
```

---

## Contributing

When adding new scripts:
1. Follow the existing naming convention
2. Add colored output for clarity
3. Include error handling (`set -e`)
4. Add usage documentation
5. Update this README
6. Make executable: `chmod +x scripts/new_script.sh`

---

## Additional Resources

- **CLAUDE.md** - Development guidelines
- **ARCHITECTURE_ANALYSIS.md** - System architecture
- **QUICK_REFERENCE.md** - Code examples
- **features.json** - Feature catalog

---

**Last Updated:** December 8, 2025
