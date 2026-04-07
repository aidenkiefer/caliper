const isProd =
  process.env.NODE_ENV === "production" || process.env.VERCEL_ENV === "production";

// Demo mode is allowed for local/dev UX iteration, but must never be enabled in production.
export const DEMO_MODE = !isProd && process.env.NEXT_PUBLIC_DEMO_MODE === "true";
