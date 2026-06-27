---
name: container-image-hygiene
description: Build minimal, non-root, single-concern container images to reduce attack surface, image size, and startup time.
discipline: infra
tags: [docker, containers, security, kubernetes, devops]
---

# Container Image Hygiene

## When to use

Container images are large (>500 MB for a simple service), run as root, or contain unnecessary
tooling (shells, package managers, build compilers). A CVE scanner reports high or critical
vulnerabilities in the final image. Pull times are slow during deployments or autoscale events.
Security audit flags root-running containers or images that include sensitive build artifacts.

## Signal

- `docker image ls` shows a service image >500 MB that is a simple HTTP server.
- `docker inspect <image>` shows `"User": ""` — defaults to root (UID 0).
- Trivy or Grype reports CRITICAL or HIGH CVEs in base-image packages that are not needed at
  runtime (e.g., `curl`, `wget`, `apt-get` in the final stage).
- Dockerfile has a single stage with build tools, dev dependencies, and runtime in one layer.
- Secrets, `.git` directories, or test files present in the final image (verify with `docker history`
  or `dive`).
- Image tag is `latest` rather than a pinned digest — image content can change without warning.

## Why

Large images with unnecessary tools increase: (1) attack surface — a shell in the container enables
an attacker who gains code execution to explore and exfiltrate; (2) pull time — slower cold starts
and autoscaling; (3) CVE exposure — packages not needed at runtime contribute vulnerabilities.
Running as root means any container escape gives the attacker root on the host kernel.

Minimal, non-root images following the principle of least privilege are the June 2026 baseline for
production container security.

## Remediate

1. **Use multi-stage builds.** Compile in a full builder stage; copy only the runtime artifact to a
   minimal final stage:
   ```dockerfile
   # Stage 1: builder
   FROM golang:1.22-alpine AS builder
   WORKDIR /app
   COPY . .
   RUN go build -o /app/server .

   # Stage 2: runtime (distroless)
   FROM gcr.io/distroless/static-debian12
   COPY --from=builder /app/server /server
   USER nonroot:nonroot
   ENTRYPOINT ["/server"]
   ```

2. **Choose a minimal base image.**
   - `gcr.io/distroless/static` or `gcr.io/distroless/base-debian12`: no shell, no package manager.
     Smallest attack surface. Best for statically-linked binaries (Go, Rust).
   - `alpine:3.x`: ~7 MB. Has a shell and `apk`. Use when you need runtime package installs or
     musl-based binaries.
   - `debian:bookworm-slim` or `ubuntu:24.04`: larger but more compatible with glibc-linked binaries.
   Never use full `ubuntu`, `debian`, or language base images (e.g., `python:3.12`) in production
   unless required — they include compilers and dev tools.

3. **Run as a non-root user.** Add a user in the Dockerfile and switch to it:
   ```dockerfile
   RUN addgroup --system app && adduser --system --ingroup app app
   USER app
   ```
   For distroless images, use the built-in `nonroot` user (UID 65532).

4. **Pin base image digests, not just tags.** Tags are mutable; digests are immutable:
   ```dockerfile
   FROM gcr.io/distroless/static-debian12@sha256:abc123...
   ```
   Use Dependabot or Renovate to automate digest updates.

5. **Remove sensitive files.** Never include `.git`, `.env`, test fixtures, or credentials in any
   stage. Use a `.dockerignore` file:
   ```
   .git
   .env
   *.test
   tests/
   node_modules/
   ```

6. **Scan images in CI for CVEs.** Run `trivy image <image>` and fail the build on CRITICAL
   severity:
   ```bash
   trivy image --exit-code 1 --severity CRITICAL myimage:latest
   ```
   Use `grype` as an alternative scanner.

7. **Use `COPY --chown=user:user`** to set ownership of copied files to the non-root user. Avoids
   runtime permission errors.

8. **Inspect the final image with `dive`.** The `dive` CLI shows layer contents and wasted space.
   Target image efficiency >95%.

## References

- Google Distroless: github.com/GoogleContainerTools/distroless
- Trivy documentation: vulnerability scanning
- Docker documentation: Multi-stage builds, .dockerignore
- CIS Docker Benchmark
- Dive: github.com/wagoodman/dive
