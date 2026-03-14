# Contributing to ShadowNet C2

First off, thank you for considering contributing to ShadowNet! It's people like you that make this tool better for the security community.

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in your interactions.

### Our Standards

**Examples of behavior that contributes to a positive environment:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Examples of unacceptable behavior:**
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues list. When you create a bug report, include as many details as possible:

**Bug Report Template:**
```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
A clear description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment:**
 - OS: [e.g. Windows 11, Ubuntu 22.04]
 - Python Version: [e.g. 3.10.5]
 - Go Version: [e.g. 1.19.2]
 - Browser: [e.g. Chrome, Firefox]

**Additional context**
Add any other context about the problem here.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any similar features** in other tools
- **Include mockups or examples** if applicable

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding standards** described below
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Write clear commit messages**
6. **Submit a pull request**

**Pull Request Template:**
```markdown
**Description**
A brief description of what this PR does.

**Motivation and Context**
Why is this change required? What problem does it solve?

**How Has This Been Tested?**
Describe the tests you ran to verify your changes.

**Types of changes**
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

**Checklist:**
- [ ] My code follows the code style of this project
- [ ] I have updated the documentation accordingly
- [ ] I have added tests to cover my changes
- [ ] All new and existing tests passed
```

## Development Guidelines

### Python Code Style

- Follow **PEP 8** style guide
- Use **type hints** where appropriate
- Write **docstrings** for all functions and classes
- Maximum line length: **100 characters**
- Use **f-strings** for string formatting

**Example:**
```python
def create_task(task_id: str, agent_id: str, command: str) -> bool:
    """
    Create a new task in the database.
    
    Args:
        task_id: Unique identifier for the task
        agent_id: ID of the target agent
        command: Command to execute
        
    Returns:
        True if task was created successfully, False otherwise
    """
    try:
        # Implementation here
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create task: {e}")
        return False
```

### Go Code Style

- Follow **official Go style guide**
- Use **gofmt** to format code
- Write **meaningful variable names**
- Add **comments for exported functions**
- Handle errors properly

**Example:**
```go
// executeCommand runs a shell command and returns the output
func executeCommand(cmd string) string {
    cmd = strings.TrimSpace(cmd)
    
    var command *exec.Cmd
    if runtime.GOOS == "windows" {
        command = exec.Command("cmd", "/C", cmd)
    } else {
        command = exec.Command("sh", "-c", cmd)
    }
    
    output, err := command.CombinedOutput()
    if err != nil {
        return err.Error() + "\n" + string(output)
    }
    
    return string(output)
}
```

### JavaScript Code Style

- Use **ES6+** syntax
- Use **const** and **let** (avoid var)
- Write **meaningful function names**
- Add **comments for complex logic**
- Use **async/await** for asynchronous code

**Example:**
```javascript
async function loadAgents() {
    try {
        const response = await fetch('/agents');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const agents = await response.json();
        renderAgents(agents);
        
    } catch (error) {
        console.error('[ERROR] Loading agents:', error);
        showErrorMessage(error.message);
    }
}
```

### Commit Message Guidelines

Follow the **Conventional Commits** specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(agent): add screenshot capture capability
fix(server): resolve session timeout issue
docs(readme): update installation instructions
refactor(database): optimize query performance
```

## Development Setup

### Setting Up Your Environment

1. **Clone your fork:**
```bash
git clone https://github.com/YOUR_USERNAME/shadownet-c2.git
cd shadownet-c2
```

2. **Create a virtual environment (Python):**
```bash
cd server
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

3. **Install Go dependencies:**
```bash
cd agent
go mod download
```

4. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
```

### Running Tests

```bash
# Python tests (when implemented)
cd server
pytest

# Go tests
cd agent
go test ./...

# Linting
cd server
pylint *.py

cd agent
golangci-lint run
```

### Testing Your Changes

- **Test on multiple platforms** (Windows, Linux, macOS)
- **Test with multiple agents** connected
- **Test error conditions** and edge cases
- **Verify UI changes** in different browsers
- **Check console for errors**

## Feature Requests

We welcome feature requests! Please:

1. **Check existing issues** first
2. **Provide clear use case** for the feature
3. **Explain expected behavior** in detail
4. **Consider security implications**
5. **Be open to discussion** and alternatives

## Security Vulnerabilities

**DO NOT** open a public issue for security vulnerabilities!

Instead:
1. Email details to: security@[project-email].com
2. Include steps to reproduce
3. Describe the potential impact
4. We will respond within 48 hours

## Documentation

- Update **README.md** for feature changes
- Update **code comments** for implementation details
- Create **wiki pages** for complex features
- Include **examples** where appropriate

## Questions?

Feel free to ask questions by:
- Opening a **GitHub Discussion**
- Posting in the **Issues** section with the `question` label
- Reaching out to maintainers

## Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **GitHub contributors** page

Thank you for contributing to ShadowNet C2! 🎉
