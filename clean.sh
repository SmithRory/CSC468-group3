#!/bin/bash

echo "Removing and puruning all containers and volumes..."

sudo docker container stop $(sudo docker ps -a -q)
sudo docker-compose down --remove-orphans
sudo docker volume prune 

echo "Finished!"
