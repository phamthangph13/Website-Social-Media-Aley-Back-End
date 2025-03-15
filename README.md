# Website-Social-Media-Aley-Back-End

## HTTPS/SSL Configuration

The application supports HTTPS for secure communication:

### Production (Render)

In production on Render, HTTPS is automatically enabled and managed by Render. All endpoints are served over HTTPS with a valid SSL certificate provided by Render.

### Development Environment

For development, you can enable HTTPS with a self-signed certificate:

1. Generate self-signed certificates:
   ```
   python generate_certs.py
   ```

2. Run the application with SSL enabled:
   ```
   export USE_SSL=True
   python app.py
   ```

The application will start with HTTPS on port 5000 (or the port specified by the PORT environment variable).

### Security Headers

The application implements the following security headers for HTTPS:

- `Strict-Transport-Security`: Enforces HTTPS connections
- `X-Content-Type-Options`: Prevents MIME type sniffing
- `X-Frame-Options`: Prevents clickjacking
- `X-XSS-Protection`: Helps prevent XSS attacks

### Email Links

All email links (verification, password reset) use HTTPS URLs to ensure secure communication.