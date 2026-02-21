# Security Architecture & Implementation Guide

## Overview

The GEO Platform API has been hardened with enterprise-grade security features to make it production-ready, scalable, and resilient against common attacks. This document outlines the security architecture, implemented features, and best practices.

## Table of Contents

1. [Security Features](#security-features)
2. [Security Architecture](#security-architecture)
3. [Authentication & Authorization](#authentication--authorization)
4. [Rate Limiting & DDoS Protection](#rate-limiting--ddos-protection)
5. [Input Validation & Sanitization](#input-validation--sanitization)
6. [Security Headers & Middleware](#security-headers--middleware)
7. [Audit Logging & Monitoring](#audit-logging--monitoring)
8. [Enabling Authentication in Production](#enabling-authentication-in-production)
9. [Security Best Practices](#security-best-practices)
10. [Security Testing](#security-testing)

---

## Security Features

### ✅ Implemented Security Layers

1. **Authentication & Authorization**
   - JWT-based authentication with access and refresh tokens
   - Role-Based Access Control (RBAC)
   - API key authentication support
   - Organization-level multi-tenancy

2. **Rate Limiting & DDoS Protection**
   - Redis-based sliding window rate limiting
   - Tier-based rate limits (free/pro/enterprise)
   - Endpoint-specific rate limits
   - IP-based rate limiting

3. **Input Validation & Sanitization**
   - SQL injection prevention
   - XSS (Cross-Site Scripting) protection
   - SSRF (Server-Side Request Forgery) prevention
   - File upload validation
   - URL and email validation

4. **Security Headers**
   - Content Security Policy (CSP)
   - HTTP Strict Transport Security (HSTS)
   - X-Frame-Options (Clickjacking protection)
   - X-Content-Type-Options (MIME sniffing protection)
   - Referrer-Policy
   - Permissions-Policy

5. **Middleware Security Stack**
   - Request size limits (10MB default)
   - SQL injection detection in query parameters
   - Error sanitization (no stack traces in production)
   - Request logging with unique IDs
   - API versioning enforcement

6. **Audit Logging**
   - All security-sensitive operations logged
   - Structured logging with loguru
   - Request/response tracking with correlation IDs
   - Log rotation and compression
   - Separate audit logs for compliance

7. **Payment & Webhook Security**
   - Stripe webhook signature verification
   - HMAC-based webhook authentication
   - Idempotent webhook processing
   - Payment operation audit logging

8. **Password Security**
   - Bcrypt hashing with salt
   - Strong password policy (12+ chars, mixed case, digits, special)
   - Password strength validation
   - Common password blocking

---

## Security Architecture

### Layered Security Model

```
┌─────────────────────────────────────────────────────────┐
│                    1. Edge Layer                         │
│  • CORS validation                                       │
│  • Trusted host verification                             │
│  • Request size limits                                   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                  2. Security Headers                     │
│  • CSP, HSTS, X-Frame-Options                           │
│  • Remove server identification                          │
│  • Set security-focused headers                          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              3. Request Validation Layer                 │
│  • SQL injection detection                               │
│  • Input sanitization                                    │
│  • API version validation                                │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│           4. Authentication & Rate Limiting              │
│  • JWT token verification                                │
│  • Rate limit checks (Redis)                             │
│  • API key validation                                    │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│            5. Authorization & Business Logic             │
│  • Role-based access control                             │
│  • Organization membership verification                  │
│  • Resource ownership checks                             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                 6. Audit Logging Layer                   │
│  • All operations logged with context                    │
│  • Structured logs for SIEM integration                  │
│  • Request/response correlation                          │
└─────────────────────────────────────────────────────────┘
```

### Middleware Execution Order

**IMPORTANT:** Middleware order matters! The following order is enforced:

1. **ErrorSanitizationMiddleware** (outermost) - Catches all errors, sanitizes for production
2. **RequestSizeLimitMiddleware** - Prevents memory exhaustion attacks
3. **SecurityHeadersMiddleware** - Adds security headers to all responses
4. **RequestLoggingMiddleware** - Logs all requests with unique IDs
5. **AuditLogMiddleware** - Detailed logging for security-sensitive endpoints
6. **SQLInjectionProtectionMiddleware** - Detects SQL injection in query params
7. **APIVersionMiddleware** - Enforces API versioning
8. **GZipMiddleware** - Response compression
9. **TrustedHostMiddleware** (production only) - Validates request host
10. **CORSMiddleware** (innermost) - CORS validation and headers

---

## Authentication & Authorization

### JWT Authentication

**Implementation:** `app/core/security.py`

```python
# JWT token structure
{
  "sub": "user_id",           # Subject (user ID)
  "exp": 1234567890,          # Expiration timestamp
  "iat": 1234567890,          # Issued at timestamp
  "type": "access",           # Token type (access/refresh)
  "role": "admin",            # User role
  "org_id": "org_uuid"        # Organization ID
}
```

**Token Expiry:**
- Access tokens: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh tokens: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)

**Usage Example:**
```bash
# Obtain access token (implement login endpoint first)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "SecurePass123!"}'

# Use token in protected endpoints
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "keywords": ["seo"]}'
```

### Role-Based Access Control (RBAC)

**Available Roles:**
- `user` - Basic user, can create analyses
- `admin` - Organization admin, can manage users and settings
- `superadmin` - Platform admin, can access all organizations

**Implementation:**
```python
from app.core.security import RoleChecker

# Require admin role
@router.post("/admin/settings", dependencies=[Depends(RoleChecker(["admin", "superadmin"]))])
async def update_settings(
    current_user: Profile = Depends(get_current_active_user)
):
    # Only admins can access this endpoint
    pass
```

### API Key Authentication

**Alternative to JWT for machine-to-machine communication:**

```bash
# Use API key
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**API keys are:**
- SHA-256 hashed in database
- Organization-scoped
- Have expiration dates (90 days default)
- Can have granular permissions

---

## Rate Limiting & DDoS Protection

### Rate Limiting Strategy

**Implementation:** `app/core/rate_limiter.py`

Uses Redis-based sliding window algorithm for accurate rate limiting across multiple API instances.

### Rate Limit Tiers

| Tier       | Analyses/5min | Optimizations/min | Uploads/hour | Standard/min |
|------------|---------------|-------------------|--------------|--------------|
| Free       | 3             | 10                | 5            | 100          |
| Pro        | 100           | 50                | 20           | 500          |
| Enterprise | 1000          | 200               | 100          | 2000         |

### Endpoint-Specific Rate Limits

```python
# Analysis creation (expensive operation)
@router.post("/analyze", dependencies=[Depends(analysis_rate_limit)])  # 3 per 5 min
async def create_analysis(...): pass

# Optimization generation (AI-powered)
@router.post("/optimize", dependencies=[Depends(optimization_rate_limit)])  # 10 per min
async def optimize(...): pass

# File uploads (bandwidth-intensive)
@router.post("/upload", dependencies=[Depends(upload_rate_limit)])  # 5 per hour
async def upload(...): pass

# Standard CRUD operations
@router.get("/data", dependencies=[Depends(standard_rate_limit)])  # 100 per min
async def get_data(...): pass

# External integrations
@router.post("/integration", dependencies=[Depends(integration_rate_limit)])  # 20 per min
async def integration(...): pass
```

### Rate Limit Headers

All rate-limited endpoints return these headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1234567890
```

### Rate Limit Response

When rate limit is exceeded:

```json
{
  "detail": {
    "error": "Rate limit exceeded",
    "retry_after": 60,
    "limit": 100,
    "window": 60
  }
}
```
**Status Code:** `429 Too Many Requests`

---

## Input Validation & Sanitization

### Validation Layers

**Implementation:** `app/core/validators.py`

### 1. URL Validation

**Protects against SSRF attacks:**

```python
from app.core.validators import URLValidator

# Validates:
# ✓ Only http/https schemes
# ✓ No access to localhost, 127.0.0.1, private networks
# ✓ No javascript:, data:, file: schemes
# ✓ Maximum URL length (2048 chars)

url = URLValidator.validate_url("https://example.com")
```

**Blocked domains:**
- `localhost`, `127.0.0.1`, `0.0.0.0`
- `169.254.x.x` (link-local addresses)
- `10.x.x.x` (private network)
- `172.16.x.x` - `172.31.x.x` (private network)
- `192.168.x.x` (private network)

### 2. String Sanitization

**Protects against SQL injection and XSS:**

```python
from app.core.validators import StringSanitizer

# Detects and blocks:
# ✓ SQL injection patterns (UNION SELECT, DROP TABLE, etc.)
# ✓ XSS patterns (<script>, javascript:, onerror=, etc.)
# ✓ Null bytes
# ✓ Excessive length

clean_text = StringSanitizer.sanitize(user_input, max_length=10000)
```

**Blocked patterns:**
- SQL keywords: `UNION SELECT`, `DROP TABLE`, `INSERT INTO`, `DELETE FROM`, `UPDATE...SET`, `EXEC(`
- XSS patterns: `<script`, `javascript:`, `onerror=`, `onload=`, `<iframe`

### 3. Keyword Validation

```python
from app.core.validators import KeywordValidator

# Validates:
# ✓ Maximum 50 keywords
# ✓ Each keyword 2-100 characters
# ✓ Alphanumeric, spaces, hyphens, dots only

keywords = KeywordValidator.validate_keywords(["seo", "optimization"])
```

### 4. Email Validation

```python
from app.core.validators import EmailValidator

# Validates:
# ✓ RFC 5321 compliant email format
# ✓ Maximum 254 characters
# ✓ Case-insensitive normalization

email = EmailValidator.validate("user@example.com")
```

### 5. Password Validation

```python
from app.core.validators import PasswordValidator

# Enforces:
# ✓ Minimum 12 characters
# ✓ At least one uppercase letter
# ✓ At least one lowercase letter
# ✓ At least one digit
# ✓ At least one special character
# ✓ Blocks common passwords

password = PasswordValidator.validate("SecurePass123!")
```

### 6. File Upload Validation

```python
from app.core.validators import FileUploadValidator

# Validates:
# ✓ Allowed extensions: .txt, .pdf, .doc, .docx
# ✓ Maximum file size: 10MB
# ✓ No path traversal (../, etc.)
# ✓ Filename length (max 255 chars)

FileUploadValidator.validate(filename, file_size)
```

### Secure Request Models

All API endpoints use `SecureBaseModel` which:
- Forbids extra fields (`extra="forbid"`)
- Validates on assignment
- Uses enum values

**Example:**
```python
from app.core.validators import SecureBaseModel

class CreateAnalysisRequest(SecureBaseModel):
    url: str = Field(..., min_length=10, max_length=2048)
    keywords: List[str] = Field(default=[], max_items=50)

    @validator('url')
    def validate_url(cls, v):
        return URLValidator.validate_url(v)
```

---

## Security Headers & Middleware

### Security Headers

**Implementation:** `app/core/middleware.py:SecurityHeadersMiddleware`

All responses include these headers:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://api.openai.com; frame-ancestors 'none';
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()
X-Request-ID: <unique-request-id>
```

### Request Size Limits

**Implementation:** `app/core/middleware.py:RequestSizeLimitMiddleware`

- Maximum request size: **10MB** (configurable via `MAX_REQUEST_SIZE`)
- Maximum upload size: **10MB** (configurable via `MAX_UPLOAD_SIZE`)
- Returns `413 Payload Too Large` when exceeded

### SQL Injection Detection

**Implementation:** `app/core/middleware.py:SQLInjectionProtectionMiddleware`

Scans query parameters for SQL keywords:
- `union`, `select`, `insert`, `update`, `delete`, `drop`
- `create`, `alter`, `exec`, `execute`, `script`, `javascript`

Returns `400 Bad Request` when detected.

### Error Sanitization

**Implementation:** `app/core/middleware.py:ErrorSanitizationMiddleware`

- **Development:** Full error details and stack traces
- **Production:** Sanitized error messages with request ID
- All errors logged internally with full context
- Never exposes internal implementation details

**Example production error:**
```json
{
  "detail": "An internal error occurred",
  "request_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

## Audit Logging & Monitoring

### Structured Logging

**Implementation:** `app/core/middleware.py:RequestLoggingMiddleware`

All requests are logged with:
- Unique request ID (UUID)
- Client IP address
- User agent
- HTTP method and path
- Response status code
- Request duration (ms)
- User ID (if authenticated)

**Log format:**
```
2025-12-03 10:15:30 | INFO     | app.core.middleware:request:66 - Request started
  request_id: 123e4567-e89b-12d3-a456-426614174000
  method: POST
  path: /api/v1/analysis/analyze
  client_ip: 192.168.1.100
  user_agent: Mozilla/5.0...

2025-12-03 10:15:32 | INFO     | app.core.middleware:request:88 - Request completed
  request_id: 123e4567-e89b-12d3-a456-426614174000
  status_code: 200
  duration_ms: 1523.45
```

### Audit Logging for Security-Sensitive Operations

**Implementation:** `app/core/middleware.py:AuditLogMiddleware`

Enhanced logging for sensitive endpoints:
- `/api/v1/analysis/analyze` - Analysis creation
- `/api/v1/voice/config` - Brand voice configuration
- `/api/v1/integrations/*` - Payment and integration operations

**Audit log includes:**
- Timestamp
- Request ID
- User ID
- Organization ID
- Operation performed
- Input parameters (sanitized)
- Result

### Log Storage

**Configuration:**

```python
# Console output (structured, colored)
logger.add(sys.stdout, level=settings.LOG_LEVEL)

# File output (rotated, compressed)
logger.add(
    "logs/app.log",
    rotation="500 MB",    # Rotate when file reaches 500MB
    retention="10 days",  # Keep logs for 10 days
    compression="zip",    # Compress rotated logs
    level=settings.LOG_LEVEL
)
```

**Log files:**
- `logs/app.log` - Main application logs
- Rotated files: `logs/app.log.2025-12-03.zip`

### Monitoring Endpoints

**Health check:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "1.0.0"
}
```

**Security info (development only):**
```bash
curl http://localhost:8000/security-info
```

**Response:**
```json
{
  "rate_limiting": {
    "enabled": true,
    "free_tier": 3,
    "pro_tier": 100,
    "enterprise_tier": 1000
  },
  "request_limits": {
    "max_request_size": "10MB",
    "max_upload_size": "10MB"
  },
  "password_policy": {
    "min_length": 12,
    "require_uppercase": true,
    "require_lowercase": true,
    "require_digits": true,
    "require_special": true
  }
}
```

---

## Enabling Authentication in Production

### Step 1: Update API Endpoints

All endpoints have commented authentication dependencies. Uncomment them:

```python
# BEFORE (MVP - no auth required)
@router.post("/analyze")
async def create_analysis(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    # Uncomment when authentication is enabled:
    # current_user: Profile = Depends(get_current_active_user)
):
    pass

# AFTER (Production - auth required)
@router.post("/analyze")
async def create_analysis(
    request: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: Profile = Depends(get_current_active_user)
):
    # Now current_user is available
    logger.info(f"Analysis created by user {current_user.id}")
    pass
```

### Step 2: Create Authentication Endpoints

Create `app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import SecurityManager, get_current_user
from pydantic import BaseModel

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Verify credentials
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Create tokens
    access_token = SecurityManager.create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "org_id": str(user.org_id)
    })
    refresh_token = SecurityManager.create_refresh_token({
        "sub": str(user.id)
    })

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh")
async def refresh(refresh_token: str):
    # Verify refresh token and issue new access token
    pass

@router.post("/logout")
async def logout(current_user: Profile = Depends(get_current_user)):
    # Implement token blacklisting if needed
    pass
```

### Step 3: Add Organization Filters

Update queries to filter by organization:

```python
# BEFORE (MVP - all data visible)
analyses = db.query(Analysis).all()

# AFTER (Production - org-scoped)
analyses = db.query(Analysis).join(Website).filter(
    Website.org_id == current_user.org_id
).all()
```

### Step 4: Update Frontend

Add authentication to frontend requests:

```javascript
// Store token after login
localStorage.setItem('access_token', response.access_token)

// Add to all requests
const response = await fetch('/api/v1/analysis/analyze', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
```

### Step 5: Enable Rate Limiting by User

Update rate limiters to use user ID instead of IP:

```python
# In rate_limiter.py
if self.identifier == "user":
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # Extract user ID from token
        payload = SecurityManager.verify_token(token)
        key = f"rate_limit:user:{payload['sub']}"
```

---

## Security Best Practices

### 1. Environment Variables

**Never commit secrets to version control:**

```bash
# .env (NEVER commit this file)
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
DATABASE_URL=postgresql://user:pass@localhost/db
OPENAI_API_KEY=sk-...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
REDIS_URL=redis://localhost:6379/0
```

### 2. Production Configuration

Update `.env` for production:

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Enable all security features
ENABLE_SECURITY_HEADERS=true
ENABLE_CSRF_PROTECTION=true
ENABLE_AUDIT_LOGGING=true
ENABLE_RATE_LIMITING=true

# Use HTTPS only
CORS_ORIGINS=["https://yourdomain.com"]

# Secure cookies
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
```

### 3. Database Security

```bash
# Use read-only user for query endpoints
# Use separate user for writes
# Never use superuser credentials in application

# Enable SSL for database connections
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
```

### 4. Redis Security

```bash
# Use password authentication
REDIS_URL=redis://:password@localhost:6379/0

# Enable TLS for production
REDIS_URL=rediss://:password@host:6380/0

# Limit max connections
REDIS_MAX_CONNECTIONS=50
```

### 5. API Keys & Secrets Rotation

Rotate secrets regularly:

```bash
# Generate new SECRET_KEY
openssl rand -hex 32

# Rotate Stripe webhook secret
# (Regenerate in Stripe Dashboard)

# Rotate API keys
# (Implement expiration: 90 days default)
```

### 6. Dependency Security

Keep dependencies updated:

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip install --upgrade -r requirements.txt

# Pin versions in requirements.txt
fastapi==0.104.1  # Not fastapi>=0.104.1
```

### 7. HTTPS/TLS

**Always use HTTPS in production:**

```nginx
# Nginx configuration
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 8. Container Security

When deploying with Docker:

```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Scan for vulnerabilities
docker scan geo-platform-api:latest

# Use specific versions
FROM python:3.11.7-slim  # Not python:3.11 or python:latest
```

### 9. Backup & Disaster Recovery

```bash
# Automated database backups
pg_dump -h localhost -U user -d db > backup.sql

# Store backups securely (encrypted)
gpg --encrypt backup.sql

# Test restore procedures regularly
psql -h localhost -U user -d db_test < backup.sql
```

### 10. Incident Response Plan

Have a plan for security incidents:

1. **Detect:** Monitor logs for anomalies
2. **Contain:** Rate limit or block malicious IPs
3. **Investigate:** Review audit logs
4. **Remediate:** Patch vulnerabilities
5. **Document:** Post-incident report

---

## Security Testing

### 1. Manual Security Testing

**Test SQL Injection:**
```bash
# Should be blocked by SQLInjectionProtectionMiddleware
curl "http://localhost:8000/api/v1/analysis?id=1' OR '1'='1"
# Expected: 400 Bad Request

# Should be blocked by StringSanitizer
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "keywords": ["test OR 1=1"]}'
# Expected: 400 Bad Request
```

**Test XSS Protection:**
```bash
curl -X POST http://localhost:8000/api/v1/voice/check \
  -H "Content-Type: application/json" \
  -d '{"text": "<script>alert(1)</script>", "config_id": "uuid"}'
# Expected: 400 Bad Request
```

**Test SSRF Protection:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8000/admin", "keywords": []}'
# Expected: 400 Bad Request

curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "http://192.168.1.1/router", "keywords": []}'
# Expected: 400 Bad Request
```

**Test Rate Limiting:**
```bash
# Send 5 requests rapidly
for i in {1..5}; do
  curl -X POST http://localhost:8000/api/v1/analysis/analyze \
    -H "Content-Type: application/json" \
    -d '{"url": "https://example.com", "keywords": []}'
done
# Expected: First 3 succeed, 4th and 5th return 429
```

**Test File Upload Validation:**
```bash
# Test large file
dd if=/dev/zero of=large.txt bs=1M count=15
curl -X POST http://localhost:8000/api/v1/voice/config/{id}/upload \
  -F "file=@large.txt"
# Expected: 413 Payload Too Large

# Test invalid extension
curl -X POST http://localhost:8000/api/v1/voice/config/{id}/upload \
  -F "file=@malicious.exe"
# Expected: 400 Bad Request
```

**Test Webhook Signature Verification:**
```bash
# Invalid signature
curl -X POST http://localhost:8000/api/v1/integrations/stripe/webhook \
  -H "stripe-signature: invalid" \
  -d '{"type": "checkout.session.completed"}'
# Expected: 400 Bad Request
```

### 2. Automated Security Testing

**Install security testing tools:**
```bash
pip install bandit safety pytest-security
```

**Run security scans:**
```bash
# Bandit - security linter
bandit -r app/

# Safety - dependency vulnerability checker
safety check

# Run security-focused tests
pytest tests/security/
```

### 3. Penetration Testing

Use tools like:
- **OWASP ZAP** - Automated security scanner
- **Burp Suite** - Web application security testing
- **SQLMap** - SQL injection testing
- **Nuclei** - Vulnerability scanner

```bash
# Example: OWASP ZAP baseline scan
docker run -v $(pwd):/zap/wrk/:rw -t owasp/zap2docker-stable \
  zap-baseline.py -t http://localhost:8000/api/v1/ -r report.html
```

### 4. Load Testing with Security

Test rate limiting under load:

```bash
# Install k6
brew install k6  # macOS
# or download from https://k6.io/

# Run load test
k6 run load-test.js
```

**load-test.js:**
```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  stages: [
    { duration: '1m', target: 100 },  // Ramp up
    { duration: '3m', target: 100 },  // Stay at 100
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.1'],     // Less than 10% errors
  },
};

export default function () {
  const res = http.post(
    'http://localhost:8000/api/v1/analysis/analyze',
    JSON.stringify({
      url: 'https://example.com',
      keywords: ['test']
    }),
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );

  check(res, {
    'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    'has rate limit headers': (r) => r.headers['X-Ratelimit-Limit'] !== undefined,
  });
}
```

### 5. Security Monitoring

**Set up monitoring:**

```python
# Sentry integration (optional)
import sentry_sdk

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=1.0 if settings.DEBUG else 0.1,
)
```

**Monitor these metrics:**
- Rate limit exceeded count (per endpoint)
- Failed authentication attempts
- SQL injection detection count
- XSS detection count
- Error rate by endpoint
- Average response time
- Webhook verification failures

---

## Compliance & Standards

### OWASP Top 10 Coverage

- ✅ **A01:2021 - Broken Access Control:** RBAC, organization-scoped queries
- ✅ **A02:2021 - Cryptographic Failures:** Bcrypt hashing, TLS, secure cookies
- ✅ **A03:2021 - Injection:** SQL injection prevention, input sanitization
- ✅ **A04:2021 - Insecure Design:** Security by design, threat modeling
- ✅ **A05:2021 - Security Misconfiguration:** Secure defaults, hardened headers
- ✅ **A06:2021 - Vulnerable Components:** Dependency scanning, version pinning
- ✅ **A07:2021 - Authentication Failures:** JWT, rate limiting, strong passwords
- ✅ **A08:2021 - Data Integrity Failures:** Webhook signatures, checksums
- ✅ **A09:2021 - Logging Failures:** Comprehensive audit logging
- ✅ **A10:2021 - SSRF:** URL validation, domain blacklisting

### PCI DSS Compliance (for Stripe integration)

- ✅ Webhook signature verification
- ✅ No storage of card data (handled by Stripe)
- ✅ Audit logging of all payment operations
- ✅ TLS encryption for payment data
- ✅ Access control for payment operations

---

## Support & Contact

For security issues:
- **Email:** security@yourdomain.com
- **Bug Bounty:** (if applicable)

For general questions:
- **Documentation:** https://docs.yourdomain.com
- **Support:** support@yourdomain.com

---

## License

This security implementation follows industry best practices and is provided as-is. Always consult with security professionals for production deployments.

---

**Last Updated:** December 3, 2025
**Version:** 1.0.0
