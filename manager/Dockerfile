FROM ubuntu:bionic

WORKDIR /usr/lib

#Install dependencies
RUN apt-get update && apt-get install -y cmake openssl libssl-dev g++

# RUN git clone https://github.com/alanxz/rabbitmq-c.git && cd rabbitmq-c
# WORKDIR /usr/lib/rabbitmq-c

# RUN git checkout v0.10.0
# RUN mkdir build
# WORKDIR /usr/lib/rabbitmq-c/build

# RUN cmake .. 
# RUN cmake --build .
# RUN ls

WORKDIR /usr/manager
COPY . .

RUN mkdir build
WORKDIR /usr/manager/build
RUN cmake ..
RUN cmake --build .
CMD ["/usr/manager/build/load_balancer"]