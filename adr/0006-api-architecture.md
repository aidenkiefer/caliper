# 6. API Service Architecture

date: 2026-01-26
status: accepted

## Context

Sprint 4 introduces the API service (`services/api`) to serve the Next.js dashboard. The API layer needs to:
- Aggregate data from multiple backend services (backtest, execution, monitoring)
- Provide a unified REST interface for the dashboard
- Handle authentication and authorization
- Support real-time monitoring via polling (not WebSockets for v1)
- Protect against abuse with rate limiting

## Decision

We will implement a **FastAPI-based API service** with the following architecture:

### Service Structure
- **Router-based organization:** Separate routers per resource (`metrics`, `strategies`, `positions`, `runs`, `alerts`, `controls`)
- **Layered architecture:** Controllers → Services → Repositories → Database
- **Centralized schemas:** Pydantic models in `packages/common/api_schemas.py` shared between API and dashboard

### Authentication & Authorization
- **JWT tokens** for stateless authentication
- **Token exchange** with NextAuth.js on frontend
- **Role-based access control:** Admin-only endpoints (`/controls/*`, `PATCH /strategies/{id}`)

### Rate Limiting
- **Tiered limits:** Dashboard endpoints (100/min), admin controls (10/min), backtest triggers (5/min)
- **Implementation:** slowapi library for FastAPI
- **Headers:** Standard rate limit headers (`X-RateLimit-*`)

### Data Aggregation
- **Direct database queries:** API service queries Postgres directly (no inter-service HTTP calls)
- **Aggregation at API layer:** Metrics summary aggregates across strategies using SQL
- **Caching:** Optional Redis cache for frequently accessed data (future enhancement)

### Request/Response Flow
```
Dashboard → FastAPI Router → Auth Middleware → Rate Limiter → Controller → Service → Repository → Postgres
```

## Consequences

### Positive
- **Single source of truth:** Database is authoritative; API aggregates from DB, not from services
- **Performance:** Direct DB queries faster than inter-service HTTP calls
- **Simplicity:** No need for service mesh or complex inter-service communication
- **Type safety:** Pydantic models ensure request/response validation
- **Auto-documentation:** OpenAPI/Swagger generated automatically

### Negative
- **Tight coupling:** API service tightly coupled to database schema
- **No service isolation:** Changes to DB schema require API updates
- **Scaling concerns:** API service becomes bottleneck if not scaled horizontally
- **Cache invalidation:** If services write directly to DB, API cache may become stale

## Alternatives Considered

### 1. Inter-Service HTTP Calls
**Approach:** API service calls other services via HTTP  
**Rejected because:**
- Adds network latency
- Requires service discovery
- More complex error handling
- Services may be down while DB is available

### 2. GraphQL API
**Approach:** Use GraphQL instead of REST  
**Rejected because:**
- Overkill for v1 (dashboard has predictable queries)
- Adds complexity (GraphQL server, resolvers)
- REST is simpler and sufficient for current needs
- Can migrate to GraphQL in v2 if needed

### 3. WebSocket for Real-Time Updates
**Approach:** Use WebSockets instead of polling  
**Rejected because:**
- Adds complexity (WebSocket server, connection management)
- 5-second polling latency acceptable for Risk Level 6 trading
- Can upgrade to WebSockets in v2 if needed

## Implementation Notes

- **Database access:** Use asyncpg or SQLAlchemy async for non-blocking queries
- **Error handling:** Consistent error response format (see `api-contracts.md`)
- **Pagination:** Offset-based pagination for list endpoints (`page`, `per_page`)
- **Versioning:** URL path versioning (`/v1/`, `/v2/`) for API evolution

## Related ADRs
- ADR-0003: FastAPI Framework Selection
- ADR-0002: TimescaleDB Selection (database choice)
