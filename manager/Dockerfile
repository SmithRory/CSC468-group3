FROM rust:latest AS builder

# Install dependencies
RUN apt update
WORKDIR /app/src
RUN USER=root cargo new --bin manager
WORKDIR /app/src/manager
COPY Cargo.toml Cargo.lock ./

# Cache dependencies
RUN cargo build --release

# Build
COPY src ./src
RUN cargo install --path .

FROM debian:buster-slim
WORKDIR /app
RUN apt-get update \
    # && apt-get install -y openssl ca-certificates \
    && apt clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY --from=builder /app/src/manager/target/release/manager ./
CMD ["/app/manager"]