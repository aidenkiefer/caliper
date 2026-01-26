# Vercel Deployment Runbook

## Prerequisites

- Vercel account (free tier is sufficient)
- GitHub repository connected to Vercel
- Environment variables configured

## Initial Setup

### 1. Connect Repository

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New..." → "Project"
3. Import your Git repository
4. Select the `quant` repository
5. **Important:** Set root directory to `apps/dashboard`

### 2. Configure Build Settings

Vercel should auto-detect Next.js, but verify:
- **Framework Preset:** Next.js
- **Root Directory:** `apps/dashboard`
- **Build Command:** `npm run build` (default)
- **Output Directory:** `.next` (default)
- **Install Command:** `npm install` (default)

### 3. Configure Environment Variables

In Vercel project settings → Environment Variables, add:

#### Required Variables

```
NEXT_PUBLIC_API_URL=https://your-api-domain.com
NEXTAUTH_URL=https://your-dashboard-domain.vercel.app
NEXTAUTH_SECRET=<generate with: openssl rand -base64 32>
```

#### Variable Scoping

- **Production:** Use for main branch deployments
- **Preview:** Use for PR preview deployments
- **Development:** Use for local development (optional)

### 4. Deploy

1. Push to `main` branch
2. Vercel automatically deploys
3. Monitor build logs in Vercel dashboard
4. Verify deployment at production URL

## Deployment Workflow

### Production Deployment

1. Merge PR to `main` branch
2. Vercel automatically triggers deployment
3. Monitor build logs:
   - Go to Vercel Dashboard → Your Project → Deployments
   - Click on the deployment to see logs
4. Verify deployment:
   - Check production URL
   - Test API connectivity
   - Verify environment variables are set

### Preview Deployment

1. Create a Pull Request
2. Vercel automatically creates preview URL
3. Preview URL format: `https://your-project-<hash>.vercel.app`
4. Test changes at preview URL
5. Merge when ready (triggers production deployment)

## Troubleshooting

### Build Fails

**Common Issues:**

1. **Missing Dependencies**
   - Check `package.json` has all required dependencies
   - Verify `npm install` completes successfully locally

2. **TypeScript Errors**
   - Fix type errors before deploying
   - Run `npm run build` locally to catch errors

3. **Environment Variables Not Set**
   - Verify all required variables are set in Vercel
   - Check variable names match exactly (case-sensitive)
   - Ensure `NEXT_PUBLIC_` prefix for client-side variables

### API Connection Issues

1. **CORS Errors**
   - Verify FastAPI backend allows Vercel domain
   - Check `CORS_ORIGINS` in `services/api/main.py` includes Vercel domains

2. **API URL Incorrect**
   - Verify `NEXT_PUBLIC_API_URL` is set correctly
   - Check API rewrites in `next.config.mjs`
   - Test API endpoint directly: `curl https://your-api.com/v1/health`

3. **Network Timeout**
   - Check FastAPI backend is running and accessible
   - Verify firewall/security group allows Vercel IPs

### Environment Variables Not Working

1. **Client-Side Variables**
   - Must have `NEXT_PUBLIC_` prefix
   - Redeploy after changing (variables are baked into build)

2. **Server-Side Variables**
   - Can use any name (no prefix required)
   - Available in API routes and Server Components

3. **Variable Scope**
   - Check variable is set for correct environment (Production/Preview)
   - Preview deployments use Preview-scoped variables

## Rollback

### Rollback to Previous Deployment

1. Go to Vercel Dashboard → Your Project → Deployments
2. Find previous working deployment
3. Click "..." menu → "Promote to Production"
4. Confirm rollback

### Rollback via Git

1. Revert commit in Git
2. Push to `main`
3. Vercel automatically deploys previous version

## Monitoring

### Vercel Analytics

- Built-in performance monitoring
- View in Vercel Dashboard → Analytics
- Track Core Web Vitals, page views, etc.

### Logs

- Real-time function logs in Vercel Dashboard
- View logs: Project → Functions → Select function
- Useful for debugging API route issues

### Alerts

- Configure in Vercel Settings → Notifications
- Get alerts for:
  - Failed deployments
  - Build errors
  - Function errors

## Security Considerations

### Environment Variables

- **Never commit secrets to Git**
- Use Vercel environment variables for all secrets
- Rotate secrets regularly

### Headers

- Security headers configured in `vercel.json`
- Includes:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`

### API Security

- FastAPI backend should validate requests
- Use authentication tokens for API calls
- Rate limit API endpoints

## Best Practices

1. **Always test locally first**
   - Run `npm run build` before pushing
   - Test API connectivity locally

2. **Use preview deployments**
   - Test changes in preview before merging
   - Share preview URLs for review

3. **Monitor deployments**
   - Check build logs for warnings
   - Verify deployment health after deploy

4. **Keep dependencies updated**
   - Regularly update npm packages
   - Test updates in preview first

5. **Document environment variables**
   - Keep `.env.example` up to date
   - Document required variables in README

## Next Steps

After successful deployment:

1. Configure custom domain (optional)
2. Set up monitoring and alerts
3. Configure CI/CD for automated testing
4. Set up staging environment (optional)
