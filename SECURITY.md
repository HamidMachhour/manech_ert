# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in ERT Station, please email **security@manech_ert.local** instead of using the issue tracker. This allows us to fix the vulnerability before public disclosure.

**Please include:**
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

We take all security reports seriously and will respond within 48 hours.

## Security Guidelines

### For Users

1. **Keep dependencies updated**
   ```bash
   composer update
   pip install --upgrade -r requirements.txt
   ```

2. **Use strong database passwords**
   - Never use default credentials in production
   - Rotate passwords regularly

3. **Enable HTTPS only**
   - Use SSL/TLS certificates (Let's Encrypt)
   - Set `APP_URL=https://`

4. **Restrict database access**
   - Limit database user privileges
   - Use firewalls to restrict network access

5. **Monitor logs**
   - Regular log review
   - Set up alerts for errors
   - Monitor for suspicious activity

### For Developers

1. **Input Validation**
   ```php
   $validated = $request->validate([
       'name' => 'required|string|max:255',
       'spacing' => 'required|numeric|min:0.1|max:100',
   ]);
   ```

2. **Use Prepared Statements**
   ```php
   // ✅ Good
   $users = User::where('email', $email)->get();
   
   // ❌ Bad
   DB::raw("SELECT * FROM users WHERE email = '$email'");
   ```

3. **Sanitize Output**
   ```blade
   <!-- ✅ Good - automatically escaped -->
   {{ $user->name }}
   
   <!-- ❌ Bad - unescaped HTML -->
   {!! $user->name !!}
   ```

4. **Use CSRF Protection**
   ```blade
   <!-- Automatically protected by Laravel -->
   <form method="POST">
       @csrf
   </form>
   ```

5. **Authentication & Authorization**
   ```php
   // Check if authenticated
   if (Auth::check()) {
       // User is logged in
   }
   
   // Check authorization
   $this->authorize('update', $scan);
   ```

## Dependency Security

### Regular Updates

```bash
# Check for vulnerabilities
composer audit
pip audit

# Update dependencies
composer update
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

### Locked Dependencies

- `composer.lock` ensures reproducible builds
- `venv/` is environment-specific
- Always commit lock files to version control

## Environment Security

### Sensitive Data Protection

**Never commit:**
- `.env` files
- Database credentials
- API keys
- Private keys
- SSH keys

**Always use:**
- `.env.example` (with dummy values)
- Environment variables
- Secrets management (GitHub Secrets, AWS Secrets Manager)

### Production Environment

**Set in `.env`:**
```env
APP_ENV=production
APP_DEBUG=false
DB_PASSWORD=<strong-random-password>
```

**Generate secure secrets:**
```bash
php artisan key:generate
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Database Security

### User Privileges

```sql
-- Create limited database user
CREATE USER 'ert_user'@'localhost' IDENTIFIED BY 'strong_password';

-- Grant only necessary privileges
GRANT SELECT, INSERT, UPDATE ON ert_station.* TO 'ert_user'@'localhost';
FLUSH PRIVILEGES;

-- Avoid using root user in application
```

### Data Protection

- Enable MySQL SSL connections in production
- Use encrypted backups
- Restrict direct database access to application server only
- Regular database audits

## API Security

### Rate Limiting

```php
// Example: Limit to 60 requests per minute
Route::middleware('throttle:60,1')->group(function () {
    Route::get('/scan/{id}/points', [...]);
});
```

### CORS Configuration

```php
// config/cors.php
'allowed_origins' => ['https://yourdomain.com'],
'supports_credentials' => true,
```

### Input Validation

Always validate API requests:
```php
$request->validate([
    'scan_id' => 'required|integer|exists:scans,id',
    'page' => 'integer|min:1',
]);
```

## Infrastructure Security

### Firewall Rules

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 3306/tcp   # Block direct DB access
sudo ufw enable
```

### SSL/TLS Configuration

```nginx
# Use strong ciphers only
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
```

### Logging & Monitoring

```bash
# Monitor for attacks
tail -f /var/log/nginx/access.log | grep -E "(union|select|drop|insert|exec)"

# Review failed logins
grep "Failed" /var/log/auth.log
```

## Security Testing

### Automated Scanning

```bash
# PHP security check
composer audit

# Python package audit
pip audit

# OWASP dependency check
# https://jeremylong.github.io/DependencyCheck/
```

### Manual Testing

1. **SQL Injection**
   ```
   Test: ' OR '1'='1
   Expected: Sanitized/rejected
   ```

2. **XSS Attacks**
   ```
   Test: <script>alert('xss')</script>
   Expected: Escaped as text
   ```

3. **CSRF Protection**
   - Verify CSRF tokens in forms
   - Test missing token handling

4. **Authentication**
   - Test forced login requirement
   - Verify session timeout
   - Check authorization boundaries

## Compliance

### Standards Followed

- **OWASP Top 10** - Web application security
- **CWE/SANS Top 25** - Software weaknesses
- **PSR-12** - PHP coding standards
- **PEP 8** - Python coding standards

### Data Protection

If handling personal data, ensure compliance with:
- GDPR (EU)
- CCPA (California)
- Local data protection laws

## Security Incidents

### Incident Response Plan

1. **Identify** - Detect security issue
2. **Isolate** - Limit damage/exposure
3. **Notify** - Inform affected parties if needed
4. **Fix** - Apply patch/remediation
5. **Monitor** - Ensure resolution
6. **Review** - Post-incident analysis

### Emergency Contacts

- Security Team: security@manech_ert.local
- On-call: [contact info]
- External: [external security team if applicable]

## Security Updates

### Release Cycle

- **Critical** - Released immediately
- **High** - Released within 1 week
- **Medium** - Released with next version
- **Low** - Released with regular updates

### Receiving Updates

- Watch GitHub releases
- Subscribe to security mailing list
- Set up dependency alerts (GitHub, Dependabot)

## Useful Resources

- [OWASP Top 10](https://owasp.org/Top10/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Laravel Security](https://laravel.com/docs/security)
- [NIST Cybersecurity](https://www.nist.gov/cyberframework)

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-23 | Initial security policy |

---

**Last Updated:** May 23, 2026

Thank you for helping keep ERT Station secure! 🔒
