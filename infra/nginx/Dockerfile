# =============================================================================
# RepoPilot — Nginx Reverse Proxy
# =============================================================================
FROM nginx:1.25-alpine

# Remove the default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom config
COPY nginx.conf /etc/nginx/conf.d/repopilot.conf

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1
