# mTLS Sidecar for Kolay MCP Proxy

Mutual TLS (mTLS) ensures only clients with a valid certificate signed by your CA can connect — even if the endpoint URL is publicly known.

## Generate Certificates

```bash
# 1. Create your private Certificate Authority
openssl req -x509 -newkey rsa:4096 -keyout ca.key -out ca.crt \
  -days 3650 -nodes -subj "/CN=Kolay mTLS CA"

# 2. Generate a server certificate (for NGINX)
openssl req -newkey rsa:2048 -keyout server.key -out server.csr \
  -nodes -subj "/CN=your-domain.com"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 365

# 3. Generate a client certificate (for each AI client)
openssl req -newkey rsa:2048 -keyout client.key -out client.csr \
  -nodes -subj "/CN=claude-desktop"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt -days 365
```

## Deploy with Docker Compose

```yaml
services:
  nginx-mtls:
    build: ./infra/nginx-mtls
    ports:
      - "443:443"
    volumes:
      - ./certs:/certs:ro
    depends_on:
      - mcp

  mcp:
    build: .
    command: python app.py
    environment:
      - KOLAY_API_TOKEN=${KOLAY_API_TOKEN}
    expose:
      - "8080"
```

## Test

```bash
# Without client cert (should fail)
curl https://your-domain.com/mcp --cacert certs/ca.crt
# -> 400 No required SSL certificate was sent

# With client cert (should succeed)
curl https://your-domain.com/mcp \
  --cacert certs/ca.crt \
  --cert certs/client.crt \
  --key certs/client.key
```

## Railway Deployment

1. Create two services in your Railway project
2. **nginx-mtls**: builds from `infra/nginx-mtls/Dockerfile`, is the public service
3. **mcp**: builds from root, internal networking only (not publicly accessible)
4. Mount your certs as Railway volumes or inject via env vars
