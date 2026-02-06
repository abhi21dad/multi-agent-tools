# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it by:

1. **DO NOT** open a public issue
2. Email the maintainers directly (add your contact email)
3. Include a detailed description of the vulnerability
4. Provide steps to reproduce if possible

We will respond within 48 hours and work with you to address the issue.

## Security Best Practices

### 1. Environment Variables & Secrets

**Never commit sensitive information to version control:**
- ✅ Use `.env` file for all secrets (already in `.gitignore`)
- ✅ Use `.env.example` as a template
- ❌ Never commit API keys, tokens, or credentials
- ❌ Never hardcode secrets in Python files

**Generate strong authentication tokens:**
```bash
# Generate a secure 32-byte hex token
openssl rand -hex 32
```

### 2. API Key Security

**OpenAI API Key:**
- Store in `.env` file only
- Never share or commit to version control
- Rotate keys regularly
- Monitor usage in OpenAI dashboard
- Set usage limits to prevent unexpected charges

**Twitter API Credentials:**
- Use OAuth 2.0 when possible
- Store all 4 credentials securely (API key, secret, access token, secret)
- Enable IP whitelisting if available
- Revoke and regenerate if compromised

**Google OAuth:**
- Use OAuth 2.0 for Gmail and Drive access
- Store `credentials.json` securely (already in `.gitignore`)
- Never share refresh tokens (`token_gmail.json`, `token_drive.json`)
- Limit OAuth scopes to only what's needed

### 3. Service Authentication

**Inter-service communication:**
- Each microservice requires an authentication token
- Use different tokens for each service
- Tokens should be at least 32 characters
- Rotate tokens periodically
- Consider upgrading to JWT tokens for production

### 4. Database Security

**SQLite database (`chatbot.db`):**
- Contains conversation history and user data
- Already excluded from version control (`.gitignore`)
- Consider encryption at rest for sensitive conversations
- Implement regular backups
- Purge old conversations periodically

### 5. Input Validation

**Current limitations:**
- Limited input sanitization in tool parameters
- File paths are sandboxed but should be validated further
- Email content and recipients should be validated
- URLs should be validated before requests

**Recommendations:**
- Validate all user inputs before processing
- Sanitize file paths to prevent directory traversal
- Validate email addresses and URLs
- Implement rate limiting per user/IP

### 6. Deployment Security

**For Production:**

1. **Use HTTPS/TLS:**
   - Never run production services over HTTP
   - Use valid SSL/TLS certificates
   - Enable HSTS headers

2. **Network Security:**
   - Run services in a private network
   - Use a reverse proxy (nginx, Caddy)
   - Implement firewall rules
   - Use API gateway for external access

3. **Authentication & Authorization:**
   - Implement proper user authentication (OAuth2, JWT)
   - Add role-based access control (RBAC)
   - Require MFA for admin access
   - Session management with expiration

4. **Secrets Management:**
   - Use a secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
   - Never store secrets in environment variables in production
   - Rotate secrets regularly
   - Use separate credentials per environment (dev/staging/prod)

5. **Container Security:**
   - Run containers as non-root user
   - Keep base images updated
   - Scan images for vulnerabilities
   - Minimize image size (fewer dependencies = less attack surface)

6. **Monitoring & Logging:**
   - Log all security events
   - Monitor for suspicious activity
   - Set up alerts for failed authentication attempts
   - Redact sensitive data from logs (API keys, tokens, PII)
   - Use centralized log aggregation

### 7. Code Security

**Dependencies:**
- Keep all dependencies updated
- Use `pip-audit` or `safety` to scan for vulnerabilities
- Review dependency licenses
- Pin versions in `requirements.txt`

```bash
# Check for vulnerabilities
pip install safety
safety check

# Or use pip-audit
pip install pip-audit
pip-audit
```

**Code Quality:**
- Run static analysis (bandit, flake8)
- Enable type checking (mypy)
- Code review all changes
- Write security tests

```bash
# Security scanning with bandit
pip install bandit
bandit -r . -ll
```

### 8. Data Privacy

**User Data:**
- Conversation history contains user queries and AI responses
- May contain PII (personally identifiable information)
- Implement data retention policies
- Provide data export/deletion capabilities
- Comply with GDPR, CCPA if applicable

**Third-party Services:**
- OpenAI: Conversations are sent to OpenAI API
- Gmail: Email contents are accessed via Gmail API
- Google Drive: File contents are accessed via Drive API
- Twitter: Tweet contents are posted publicly

**Privacy Recommendations:**
- Inform users about data processing
- Obtain consent for data collection
- Implement data minimization
- Provide privacy policy
- Enable encryption in transit and at rest

### 9. Known Security Considerations

**Current Architecture:**
- Services communicate over HTTP (localhost only)
- Simple token authentication between services
- No user authentication in frontend
- No rate limiting implemented
- No request validation middleware

**For Production, Implement:**
- HTTPS/TLS for all communication
- JWT or OAuth2 for authentication
- API rate limiting
- Request validation and sanitization
- CORS headers properly configured
- CSP (Content Security Policy)
- Security headers (HSTS, X-Frame-Options, etc.)

### 10. Incident Response

**If a security breach occurs:**

1. **Immediate Actions:**
   - Revoke compromised API keys immediately
   - Disable affected services
   - Change all authentication tokens
   - Review access logs

2. **Investigation:**
   - Determine scope of breach
   - Identify affected data
   - Document timeline of events
   - Preserve evidence

3. **Recovery:**
   - Patch vulnerabilities
   - Restore from clean backups
   - Reset all credentials
   - Monitor for further suspicious activity

4. **Post-Incident:**
   - Notify affected users if required
   - Update security measures
   - Document lessons learned
   - Implement additional controls

## Security Checklist for Production

Before deploying to production, ensure:

- [ ] All `.env` variables are set in a secrets manager
- [ ] No secrets in code or version control
- [ ] HTTPS/TLS enabled for all services
- [ ] Strong authentication tokens (32+ characters)
- [ ] User authentication implemented
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Security headers configured
- [ ] Dependency vulnerabilities scanned and resolved
- [ ] Container images scanned for vulnerabilities
- [ ] Logging and monitoring configured
- [ ] Backup and disaster recovery plan in place
- [ ] Security audit completed
- [ ] Privacy policy in place
- [ ] Incident response plan documented

## Security Updates

This section will be updated as security measures are improved or vulnerabilities are discovered.

**Latest Update:** [Date]
**Version:** 1.0.0

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OpenAI Best Practices](https://platform.openai.com/docs/guides/safety-best-practices)
- [LangChain Security](https://python.langchain.com/docs/security)
- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
