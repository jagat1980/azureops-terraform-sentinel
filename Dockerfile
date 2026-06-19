FROM alpine:3.17.0
RUN apk add --no-cache openssl=3.0.8-r0 \
    && addgroup -S app \
    && adduser -S app -G app

USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 CMD openssl version >/dev/null || exit 1
