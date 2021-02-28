#!/bin/bash

echo "Removing and puruning all containers and volumes..."

docker container stop $(sudo docker ps -a -q)
docker-compose down --remove-orphans
docker volume prune 

echo "Finished!"
