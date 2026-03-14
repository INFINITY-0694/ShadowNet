# Security Policy

## Supported Versions

Currently supported versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**DO NOT** open a public issue to report a security vulnerability.

The ShadowNet team takes security bugs seriously. We appreciate your efforts to responsibly disclose your findings.

### How to Report

1. **Email**: Send details to security@[yourdomain].com
2. **PGP Key**: Available at [keyserver.com/yourkeyid]
3. **Include**:
   - Type of vulnerability
   - Full paths of source files related to the vulnerability
   - Location of the affected source code (tag/branch/commit)
   - Steps to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the issue

### Response Timeline

- **48 hours**: Initial response acknowledging receipt
- **7 days**: Detailed response with assessment
- **30 days**: Security patch release (if confirmed)

### What to Expect

- Confirmation of receipt
- Regular updates on progress
- Credit in security advisory (if desired)
- Early notification before public disclosure

## Security Best Practices

### For Users

1. **Change default credentials** immediately
2. **Use strong encryption keys** (32 random bytes)
3. **Enable HTTPS** in production environments
4. **Run in isolated networks** when possible
5. **Monitor logs** regularly
6. **Update regularly** to get security patches
7. **Limit user access** with role-based permissions

### For Developers

1. **Never commit** secrets or credentials
2. **Review code** for security issues before merging
3. **Use parameterized queries** to prevent SQL injection
4. **Validate all inputs** from users and agents
5. **Use secure random** for cryptographic operations
6. **Keep dependencies updated**
7. **Follow principle of least privilege**

## Known Security Considerations

### By Design

- This is a **penetration testing tool** designed to appear like malware
- **Administrative access** may be required for some operations
- **Network communication** is intentionally designed to be subtle
- **Encryption keys** must be kept secret

### Recommended Deployment

- **Isolated lab environment** only
- **Authorized testing** with written permission
- **Network segmentation** from production systems
- **Proper access controls** and authentication
- **Regular monitoring** and logging

## Disclosure Policy

- Security issues will be disclosed **after a fix is available**
- **30-day embargo** for critical vulnerabilities
- **Public disclosure** includes:
  - Description of the vulnerability
  - Affected versions
  - Mitigation steps
  - Credit to reporter (if approved)

## Legal Notice

Remember that this tool should only be used:
- On systems you own
- With explicit written authorization
- In compliance with all applicable laws
- For educational or authorized security testing

Unauthorized access to computer systems is illegal in most jurisdictions.
