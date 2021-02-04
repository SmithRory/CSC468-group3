# Pygang - Group 3 - Project Documentation

## Milestones
Milestone | Date | Deliverables
--------- | ---- | ------------
Initial Report & Documentation | Jan. 31st, 2021 | [Document](https://github.com/RorySmith2475/CSC468-group3/blob/main/documentation/milestones/Group3%20-%20Pygang%20-%20Initial%20Report%20and%20Documentation.pdf)<br>[Presentation](https://github.com/RorySmith2475/CSC468-group3/blob/main/documentation/milestones/Group3%20-%20Pygang%20-%20Initial%20Report%20Presentation%20Slides.pdf)

## MongoDB

- Running as a local instance in a container
- There are two user accounts:
    - `pygang_root` (pwd: pygang_root) 
        - User is created when the mongo server is initialized (see the docker-compose file)
        - User has root (admin) privilege and should not be used by the application directly 
    - `pygang_worker` (pwd: pygang_worker)
        - User is created by the init-mongo.js script. This script is copied into the continer (see docker-compose file -> mongodb -> volumes) and is automatically run by mongo when it's initialized.
        - This user has read-write access to the `pygangdb` database
        - The credentials for this user is given to the worker through environment variables.
- The database containing all collections is `pygangdb`
- The database will persist when run on the same machine as long as the volume is not deleted (see docker-compose file -> mongodb -> volumes)

### To directly interface with the mongo container:
- `docker-compose up -d` to get the container running in the background
- `docker exec -it mongodb bash` to run the shell inside the running mongodb container
- `mongo -u pygang_worker -p pygang_worker --authenticationDatabase pygangdb` to connect to the mongo instance
- Mongo shell commands can now be used with the same privilege as the worker container

### To wipe the database and all users:
- `docker-compose ps` to see all running containers
- `docker-compose stop` to stop running the containers
- `docker volume ls` to list all volumes on the machine
    - the persistent data would be listed as `csc468-group3_mongo-data`
    - if the above doesn't show up there is nothing to wipe
- `docker-compose down` to stop all containers and networks
    - the volume cannot be removed if there is something using it
- `docker volume rm csc468-group3_mongo-data` to finally delete the volume
- now when `docker-compose up -d` the user (pygang_worker) and database (pygangdb) defined in `init-mongo.js` will be created from new