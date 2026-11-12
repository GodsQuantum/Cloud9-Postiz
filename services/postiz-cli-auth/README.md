# Postiz CLI auth server (generic GHCR packaging)

The existing public Cloud9-Postiz application repository builds the official gitroomhq/postiz-agent/server with GitHub Actions. It does not fork the upstream server or include deployment data.

On successful CI, it publishes prebuilt linux/amd64 and linux/arm64 images:
- ghcr.io/godsquantum/cloud9-postiz-cli-auth:latest
- ghcr.io/godsquantum/cloud9-postiz-cli-auth:sha-<upstream-revision>

Only operators provide the runtime Postiz OAuth client ID/secret, database URL, API and frontend URLs, and server URL. Nothing production-specific goes into this public repository. The source currently needs node-fetch v2 (CommonJS interop) rather than upstream package.json's v3.
