# Security Guidelines

## Authentication & Authorization

- Implement proper authentication for all endpoints
- Use industry-standard protocols (OAuth 2.0, JWT)
- Implement role-based access control (RBAC)
- Never store passwords in plain text - use bcrypt or Argon2

## Data Protection

- Encrypt sensitive data at rest
- Use TLS for data in transit
- Never log sensitive information (passwords, tokens, PII)
- Mask sensitive data in logs and error messages

## Input Validation

- Validate all input on server-side
- Use allowlist approach for input validation
- Sanitize HTML to prevent XSS
- Use parameterized queries for database operations

## Secure Coding Practices

- Avoid using `eval()` or similar dynamic execution
- Use safe XML parsers with proper configuration
- Disable directory listing
- Set proper file permissions
- Use secure random number generators for tokens

## Dependency Management

- Keep dependencies up to date
- Regularly scan for vulnerabilities (e.g., OWASP Dependency Check)
- Verify integrity of third-party packages

## API Security

- Implement rate limiting
- Use API keys or tokens for authentication
- Validate content types
- Implement CORS properly
- Add security headers (CSP, HSTS, X-Frame-Options)
