# Security Policy

## Summary

This document defines the security policies and practices for the quantitative ML trading platform. Given that the system handles sensitive financial data and controls real money trading, security must be paramount at every layer.

**Security Principles:**
- **Least Privilege:** Services and users have minimum necessary permissions
- **Defense in Depth:** Multiple layers of security controls
- **Secrets Isolation:** API keys, credentials never in code or logs
- **Audit Everything:** All security-relevant actions logged
- **Fail Secure:** Default to deny, explicit allows

---

## Key Decisions

### ✅ Doppler for Secrets Management
**Decision:** Use Doppler (or AWS Secrets Manager/GCP Secret Manager) for secrets  
**Rationale:**
- Centralized secret storage with versioning
- Environment-specific secrets (dev/staging/prod)
- Secret rotation without code changes
- Audit logs for secret access

**Alternative:** `.env` files for local dev only (never committed to Git)

### ✅ Separate Paper and Live Credentials
**Decision:** Paper and live broker API keys are completely isolated  
**Rationale:**
- Prevents accidental live trading during testing
- Different accounts = different risk profiles
- Easier to audit live trades separately

### ✅ API Key Rotation Policy
**Decision:** Rotate broker API keys every 90 days  
**Rationale:**
- Reduces risk window if keys leaked
- Industry best practice
- Automated rotation via Doppler/Secrets Manager

### ✅ Principle of Least Privilege for Broker APIs
**Decision:** Broker API keys have minimum required permissions  
**Rationale:**
- Paper trading keys: Cannot trade live
- Live trading keys: Cannot withdraw funds (trade-only permissions)
- Data-only keys for historical data fetching (no trading)

---

## Secrets Management

### Secret Categories

| Secret Type | Example | Storage | Rotation |
|------------|---------|---------|----------|
| **Broker API Keys** | Alpaca API key/secret, IB credentials | Doppler/Secrets Manager | 90 days |
| **Database Credentials** | Postgres password | Doppler/Secrets Manager | 180 days |
| **API Tokens** | JWT secret, NextAuth secret | Doppler/Secrets Manager | Never (rotate on breach) |
| **Data Provider Keys** | Polygon API key, IEX token | Doppler/Secrets Manager | Yearly |
| **Alert Webhooks** | Slack webhook URL | Doppler/Secrets Manager | Never (rotate on breach) |

### Storage Rules

**Never Store in:**
- ❌ Git repository (even private repos)
- ❌ Docker images
- ❌ Application logs
- ❌ Error messages
- ❌ Client-side code

**Always Store in:**
- ✅ Doppler (or AWS/GCP Secrets Manager)
- ✅ `.env.local` for local dev (gitignored)
- ✅ Environment variables injected at runtime

### Environment Separation

**Local Development:**
```env
# .env.local (gitignored)
BROKER_API_KEY=paper_key_xxx  # Paper trading only
DATABASE_URL=postgresql://localhost:5432/quant_dev
MODE=PAPER
```

**Production:**
```bash
# Docker container environment (injected from Doppler)
BROKER_API_KEY=live_key_xxx  # Live trading (restricted permissions)
DATABASE_URL=postgresql://prod-db.aws.com:5432/quant_prod
MODE=LIVE
```

### Secret Injection

**Docker Compose (Local):**
```yaml
services:
  api:
    env_file:
      - .env.local
```

**Production (Docker):**
```bash
# Inject secrets from Doppler
doppler run -- docker-compose up
```

---

## Authentication & Authorization

### User Authentication

**Method:** JWT tokens (JSON Web Tokens)  
**Token Lifetime:**
- **Access Token:** 1 hour
- **Refresh Token:** 7 days

**Token Payload:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "role": "admin",  // or "viewer"
  "iat": 1706227200,  // Issued at
  "exp": 1706230800   // Expires at
}
```

**Storage:**
- Frontend: HTTP-only cookies (prevents XSS)
- Backend: Signed with `JWT_SECRET` (stored in Doppler)

### Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **admin** | Full access: view metrics, modify strategies, trigger backtests, enable/disable trading, access controls |
| **trader** | View metrics, trigger backtests, modify strategy parameters (but not enable/disable) |
| **viewer** | Read-only: view metrics, positions, runs (no modifications) |

**Implementation:** Middleware in FastAPI checks `role` claim in JWT

### Service-to-Service Authentication

**Method:** API keys with short-lived tokens  
**Example:** Data service calling Feature service

**Request:**
```
Authorization: Bearer service_token_xxx
X-Service-Name: data-service
```

**Token Generation:**
- Services generate short-lived tokens (15 minutes)
- Signed with `SERVICE_JWT_SECRET` (different from user JWT secret)

---

## Network Security

### Production Deployment

**Architecture:**
```
Internet
   ↓
[Vercel - Next.js Dashboard] ← HTTPS only
   ↓
[API Gateway / Load Balancer] ← HTTPS only, WAF enabled
   ↓
[FastAPI Backend] ← Private IP, no public access
   ↓
[Trading Services, Database] ← Private network only
```

### Firewall Rules

**API Backend:**
- Allow: HTTPS (443) from Vercel IPs
- Allow: Internal services (private network)
- Deny: All other inbound traffic

**Database:**
- Allow: PostgreSQL (5432) from API and services only (private network)
- Deny: Public internet access

**Broker API Calls:**
- Allow: Outbound HTTPS to broker domains (Alpaca, IB)
- Log all broker API requests

### IP Whitelisting

**For Live Trading:**
- **Option 1:** Whitelist production server IPs in broker account settings
- **Option 2:** Use static IP or VPN for broker API calls

---

## Data Security

### Encryption

**At Rest:**
- Database: Encrypted volumes (AWS RDS encryption, DigitalOcean encrypted disks)
- Object Storage: Server-side encryption (S3 SSE-S3 or SSE-KMS)
- Backups: Encrypted with AES-256

**In Transit:**
- All API calls: HTTPS/TLS 1.3
- Database connections: SSL/TLS enforced (`sslmode=require`)
- Internal services: TLS or VPN tunnel

### Sensitive Data Masking

**In Logs:**
- Mask API keys: `ALPACA_KEY=***********`
- Mask credentials: `password=***`
- Mask PII: email addresses, user IDs (hash or partially mask)

**In Error Messages:**
- Never expose internal stack traces to clients
- Generic error messages: "An error occurred" (log details server-side)

### Data Retention

**Logs:**
- Application logs: 30 days
- Audit logs (trades, controls): Indefinite (compliance)

**User Data:**
- Active users: Indefinite
- Deleted users: 30-day soft delete, then permanent purge

---

## Broker API Security

### Permissions Configuration

**Paper Trading API Key:**
- ✅ Read account info
- ✅ Place orders (paper only)
- ✅ Read positions
- ❌ Withdraw funds (N/A for paper)
- ❌ Access live trading

**Live Trading API Key:**
- ✅ Read account info
- ✅ Place orders (live trading)
- ✅ Read positions
- ❌ Withdraw funds (disabled at broker level)

### Broker Account Isolation

- **Paper Account:** Separate Alpaca account for paper trading
- **Live Account:** Dedicated brokerage account for live trading (no manual trading)

### API Key Validation

**Startup Check:**
```python
# Verify API key is for correct mode
if MODE == "LIVE":
    assert broker_client.is_live_account() == True
else:
    assert broker_client.is_live_account() == False
```

**Alert on Mismatch:** If mode mismatch detected, halt trading and send critical alert

---

## Audit Logging

### Events to Audit

| Event | Details Logged |
|-------|----------------|
| **User Login** | User ID, IP, timestamp, success/failure |
| **Strategy Enable/Disable** | User ID, strategy ID, action, timestamp |
| **Order Placed** | Strategy ID, symbol, quantity, price, mode (PAPER/LIVE) |
| **Risk Limit Modified** | User ID, old value, new value, timestamp |
| **Kill Switch Activated** | User ID (or system), reason, affected strategies |
| **Mode Transition** | Strategy ID, from mode, to mode, user ID, timestamp |
| **Secret Access** | Service name, secret name, timestamp |
| **Failed Authentication** | IP, email, timestamp |

### Audit Log Storage

**Database Table:** `security.audit_logs`

```sql
CREATE TABLE security.audit_logs (
    log_id          BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(100) NOT NULL,
    user_id         UUID,
    service_name    VARCHAR(100),
    details         JSONB NOT NULL,  -- Flexible event details
    ip_address      INET,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    severity        VARCHAR(20) CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL'))
);

-- Index for querying by event type and timestamp
CREATE INDEX idx_audit_event_time ON security.audit_logs (event_type, timestamp DESC);
```

### Alerting on Critical Events

**Trigger Immediate Alerts:**
- Kill switch activated
- Live trading mode enabled
- Failed login attempts (>5 in 10 minutes from same IP)
- Secret access from unknown service

**Alert Channels:**
- Slack webhook (high priority)
- Email (backup channel)
- SMS (critical events only, via Twilio)

---

## Deployment Security

### Docker Security

**Best Practices:**
- ✅ Use minimal base images (Alpine Linux)
- ✅ Run containers as non-root user
- ✅ Scan images for vulnerabilities (Snyk, Trivy)
- ✅ Secrets via environment variables (not in image)

**Dockerfile Example:**
```dockerfile
FROM python:3.11-alpine

# Create non-root user
RUN adduser -D appuser
USER appuser

# Copy code
COPY --chown=appuser:appuser . /app
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run app
CMD ["python", "main.py"]
```

### Environment Isolation

| Environment | Purpose | Secrets | Broker Mode |
|-------------|---------|---------|-------------|
| **local** | Development | `.env.local` (paper keys) | PAPER |
| **staging** | Pre-prod testing | Doppler (staging, paper keys) | PAPER |
| **production** | Live trading | Doppler (production, live keys) | LIVE |

**Never** mix staging and production secrets.

### Rollback Plan

**If Deployment Fails:**
1. Revert to previous Docker image tag
2. Restart services
3. Verify no unwanted orders placed (check broker account)
4. Alert team

**Deployment Strategy:**
- Blue-green deployments (minimize downtime)
- Canary releases (test with 1% traffic first)

---

## Incident Response

### Breach Detection

**Monitor for:**
- Unusual trading activity (e.g., orders from unknown strategy)
- API key usage from unexpected IPs
- Database access from unauthorized services
- Large withdrawals or transfers (should be impossible, but monitor)

### Response Plan

**If Credentials Leaked:**
1. **Immediate:** Revoke compromised API keys (broker, database, etc.)
2. **Immediate:** Halt all trading (activate kill switch)
3. **Within 1 hour:** Rotate all related secrets
4. **Within 24 hours:** Audit logs to identify impact
5. **Within 48 hours:** Review and patch security gap

**If Unauthorized Trades Detected:**
1. **Immediate:** Halt trading, close open positions
2. **Immediate:** Contact broker to reverse trades (if within window)
3. **Within 1 hour:** Identify how unauthorized orders were placed
4. **Within 24 hours:** Patch vulnerability, resume trading with additional controls

---

## Compliance & Legal

### Financial Regulations

**Disclaimer:** This platform is for personal use. If expanding to manage others' money, consult legal/compliance advisors for:
- SEC regulations (if in U.S.)
- Broker-dealer licensing
- Fiduciary responsibilities

### Data Privacy

**GDPR/CCPA Compliance (if applicable):**
- User data encrypted at rest
- Right to deletion (soft delete with 30-day purge)
- Data audit logs

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **API Key Leak** | Very High - Unauthorized trading | Low | Secrets manager, key rotation, IP whitelisting |
| **SQL Injection** | High - Data breach | Low | Parameterized queries (SQLAlchemy ORM), input validation |
| **XSS Attack** | Medium - Session hijack | Medium | HTTP-only cookies, CSP headers, sanitize inputs |
| **CSRF Attack** | Medium - Unauthorized actions | Medium | CSRF tokens (NextAuth.js), SameSite cookies |
| **DDoS** | High - Service unavailable | Medium | Rate limiting, WAF, Cloudflare |
| **Insider Threat** | High - Intentional sabotage | Very Low | Role-based access, audit logs, separation of duties |

---

## Open Questions

1. **Secrets Manager Choice:** Doppler, AWS, GCP, or HashiCorp Vault?
2. **WAF Configuration:** Cloudflare WAF or AWS WAF for DDoS protection?
3. **2FA:** Require two-factor authentication for admin users?
4. **Security Audits:** Frequency of penetration testing (quarterly, yearly)?
5. **Backup Encryption:** Use separate keys for backups vs live database?

---

## Next Steps

1. Set up Doppler account and configure secrets
2. Implement JWT authentication in FastAPI
3. Configure RBAC middleware
4. Set up audit logging table and triggers
5. Write incident response runbook
6. Enable database encryption (RDS/DigitalOcean)
