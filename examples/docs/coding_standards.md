# Java Coding Standards

## Naming Conventions

### Class Names
- Class names must be in UpperCamelCase
- Classes representing business objects should end with meaningful suffixes like `Service`, `Controller`, `Repository`, `Entity`, `DTO`
- Examples: `UserService`, `OrderController`, `ProductRepository`

### Method Names
- Method names must be in camelCase
- Methods should be verbs or verb phrases
- Examples: `getUserById`, `calculateTotal`, `processOrder`

### Variable Names
- Local variables should be in camelCase
- Use meaningful names that describe the purpose
- Avoid single letters except in loops

## Code Style

### Line Length
- Maximum line length: 120 characters
- Break long lines before operators

### Indentation
- Use 4 spaces for indentation
- No tabs

### Braces
- Opening brace on same line
- Closing brace on new line

## Documentation

### Javadoc
- All public methods must have Javadoc comments
- Include @param, @return, @throws tags
- Describe what the method does, not how

### Comments
- Use comments to explain WHY, not WHAT
- Keep comments up to date with code
- Avoid obvious comments

## Exception Handling

- Never swallow exceptions without logging
- Use specific exception types
- Include context in exception messages
- Don't catch generic Exception unless necessary

## Resource Management

- Always close resources in finally block or use try-with-resources
- Use connection pooling for database access
- Close streams and readers

## Security

- Never hardcode passwords or secrets
- Use environment variables or secure vaults
- Validate all input data
- Use parameterized queries to prevent SQL injection
- Sanitize output to prevent XSS
