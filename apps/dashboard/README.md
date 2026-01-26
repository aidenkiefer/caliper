# Caliper Dashboard

A modern monitoring dashboard for Caliper. Built with Next.js 14, Tailwind CSS, and Shadcn/UI.

## Features

- **Overview Dashboard**: Real-time portfolio metrics, equity curves, and alerts
- **Strategy Management**: Monitor and configure trading strategies
- **Backtest Reports**: View detailed backtest results with equity curves and trade history
- **System Health**: Monitor service status and API rate limits
- **Dark Mode**: Designed for dark mode by default (trading standard)
- **Responsive**: Mobile-first design for monitoring on any device

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + Shadcn/UI
- **Charts**: Recharts
- **Data Fetching**: SWR (polling at 5s intervals)
- **Fonts**: Inter (sans) + Geist Mono (data)

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running at `http://localhost:8000` (optional - dashboard includes mock data)

### Installation

```bash
# Navigate to dashboard directory
cd apps/dashboard

# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

### Environment Variables

Create a `.env.local` file with the following variables:

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/v1

# Optional: Authentication (not yet implemented)
# NEXTAUTH_URL=http://localhost:3000
# NEXTAUTH_SECRET=your-secret-key
```

## Project Structure

```
apps/dashboard/
├── src/
│   ├── app/
│   │   ├── (dashboard)/          # Dashboard route group
│   │   │   ├── page.tsx          # Overview (/)
│   │   │   ├── strategies/       # Strategy pages
│   │   │   ├── runs/             # Backtest run pages
│   │   │   ├── health/           # System health
│   │   │   └── settings/         # Settings page
│   │   ├── layout.tsx            # Root layout
│   │   └── globals.css           # Global styles
│   ├── components/
│   │   ├── ui/                   # Shadcn/UI components
│   │   ├── sidebar.tsx           # Navigation sidebar
│   │   ├── header.tsx            # Page header with kill switch
│   │   ├── stats-card.tsx        # Metric display card
│   │   ├── equity-chart.tsx      # Portfolio equity chart
│   │   └── alerts-widget.tsx     # Alerts display
│   └── lib/
│       ├── api.ts                # API client functions
│       ├── hooks/                # React hooks (SWR-based)
│       ├── types.ts              # TypeScript types
│       └── utils.ts              # Utility functions
├── tailwind.config.ts            # Tailwind configuration
├── tsconfig.json                 # TypeScript configuration
└── package.json                  # Dependencies
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Overview dashboard with key metrics and equity curve |
| `/strategies` | List of all trading strategies with status |
| `/strategies/[id]` | Strategy detail with performance and configuration |
| `/runs` | Backtest and trading session history |
| `/runs/[id]` | Detailed backtest report with trades |
| `/health` | System health and service status |
| `/settings` | Dashboard and platform settings |

## API Integration

The dashboard fetches data from the FastAPI backend. All hooks include mock data fallbacks for development without a running backend.

### Polling Intervals
- **Metrics**: 5 seconds
- **Alerts**: 5 seconds
- **Strategies**: 10 seconds
- **Runs**: 10 seconds
- **Health**: 10 seconds

### API Endpoints Used
- `GET /v1/metrics/summary` - Dashboard overview metrics
- `GET /v1/strategies` - Strategy list
- `GET /v1/strategies/{id}` - Strategy detail
- `GET /v1/runs` - Backtest/run history
- `GET /v1/runs/{id}` - Run detail with trades
- `GET /v1/alerts` - System alerts
- `GET /v1/health` - Service health status

## Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linting
npm run lint
```

## Color Palette

The dashboard uses a dark theme optimized for financial data:

| Token | Value | Use |
|-------|-------|-----|
| `--background` | `#09090b` | Page background |
| `--card` | `#18181b` | Card backgrounds |
| `--profit` | `#22c55e` | Positive values (green) |
| `--loss` | `#ef4444` | Negative values (red) |
| `--warning` | `#eab308` | Warnings (yellow) |

## Deployment

The dashboard is optimized for Vercel deployment:

```bash
# Deploy to Vercel
vercel
```

Or build and deploy to any Node.js host:

```bash
npm run build
npm start
```

## Related Documentation

- [Dashboard Specification](../../docs/dashboard-spec.md)
- [API Contracts](../../docs/api-contracts.md)
- [Architecture](../../docs/architecture.md)

## License

Private - Internal use only.
