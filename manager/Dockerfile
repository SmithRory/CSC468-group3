FROM rust:latest

WORKDIR /usr/src

# Create blank app
RUN USER=root cargo new manager
WORKDIR /usr/src/manager

# We want dependencies cached, so copy those first.
COPY Cargo.toml /usr/src/manager/
COPY Cargo.lock /usr/src/manager/

# This is a dummy build to get the dependencies cached.
RUN cargo build --release

# This is the actual build.
COPY src/ /usr/src/manager/src
RUN cargo build --release --verbose
RUN mv /usr/src/manager/target/release/manager /bin

WORKDIR /

# CMD ["/usr/src/manager/target/release/manager"]
CMD ["/bin/manager"]
