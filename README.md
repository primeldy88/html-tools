# HTML Tools Portal

Docker-based tool portal with upload functionality.

## Quick Start

```bash
docker pull ghcr.io/primeldy88/html-tools:latest
docker run -d -p 5000:5000 --name html-tools \
  -e ADMIN_PASSWORD=admin123 \
  ghcr.io/primeldy88/html-tools:latest
```

Then visit http://localhost:5000 (admin/admin123)
