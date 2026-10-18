---
name: a13n-http-inspection
description: Inspect an assigned HTTP service using the packaged curl, OpenSSL, Nmap, and ffuf tools, with bounded requests and evidence saved for comparison.
---

# HTTP Inspection

Start from the assigned address and port. Save response headers and a response
body separately so later checks can distinguish server behavior from tool errors:

```sh
curl --connect-timeout 10 --max-time 30 -sS -D headers.txt -o response.bin "$TARGET_URL"
file response.bin
```

Inspect redirects before following them, especially when they change the host.
Check status, content type, cookies, and the baseline body before choosing the next
request. Preserve binary responses as files instead of dumping them into context.

For JSON, use jq to select relevant fields. For TLS, use OpenSSL to distinguish a
certificate or handshake problem from an HTTP failure; do not turn off certificate
verification as a generic repair.

When service identification is needed, restrict Nmap to assigned hosts and ports.
TCP connect mode (`-sT`) works without raw-socket privileges. Do not infer that an
unavailable privileged scan means the service is absent.

Use ffuf only when a concrete HTTP hypothesis benefits from a finite set of
candidate paths or parameter values. Consult `ffuf -h` for the installed version,
bound concurrency, request rate, and duration, and compare candidates against the
baseline to recognize wildcard responses. The image contains no assumed wordlist
collection. Build a small task-relevant list in the workspace when necessary.

Record the exact command, exit status, and relevant response differences. A timeout,
tool error, or filtered response does not establish that a feature or issue is absent.
