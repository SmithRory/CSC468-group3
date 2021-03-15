# Pygang - Group 3 - Project Documentation

## Milestones
Milestone | Date | Deliverables
--------- | ---- | ------------
Initial Report & Documentation | Jan. 31st, 2021 | [Document](https://github.com/RorySmith2475/CSC468-group3/blob/main/documentation/milestones/Group3%20-%20Pygang%20-%20Initial%20Report%20and%20Documentation.pdf)<br>[Presentation](https://github.com/RorySmith2475/CSC468-group3/blob/main/documentation/milestones/Group3%20-%20Pygang%20-%20Initial%20Report%20Presentation%20Slides.pdf)

## Uvic VM setup
The following steps are needed to get the software running in the VM provided by Uvic. These steps need to be followed for every new machine accessed.
1. Clone repository: `sudo git clone https://github.com/RorySmith2475/CSC468-group3.git`
2. cd into repo folder
3. Install curl: `sudo apt install curl`
4. Install docker-compose:
    1. `sudo curl -L "https://github.com/docker/compose/releases/download/1.28.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose`
    2. `sudo chmod +x /usr/local/bin/docker-compose`
    3. `sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose`
5. Install pip3: `sudo apt install python3-pip`
6. Install pika: `sudo pip3 install pika`
7. Run the server: `sudo docker-compose up --build`

### Running Workloads
Once the VM has been setup, workloads can be run.

1. Open a seperate terminal tab in the same directory as the `docker-compose up` command was run in.
2. Run `python3 frontend_proxy.py` to send commands to the system.
    *  To run a workload file append `-f <path to workload>` to the above command.
3. To re-run a workload, remember to first delete the mongo-data docker volume to clean the database (sel below for details).

## Helpful commands
- `docker exec -it <container name> bash` to start a shell in the container
- `docker container logs <container name>` to get stdout of any container
- `docker kill <container name>` to remove a container (helpful for killing workers spun up by the manager)
- `sudo docker container stop $(sudo docker ps -a -q)`
- `sudo docker cp <containerID>:/app/testLOG ./testLOG`
- `grep --only-matching '<username>.[a-zA-Z0-9]*</username>' logfilename | sort --unique | wc -l` to find the number of users
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

### Accounts Schema  
The following is how a user account is stored within MongoDB.
```json
{"user_id": "pygang_test_user",
     "account": 1000.00,
     "available": 825.00,
     "stocks": [
         { "symbol": "ABC", "amount" : 10 },
         { "symbol": "XYZ", "amount" : 15 }
     ],
     "auto_buy": [
        { "symbol": "ABC", "amount": 5, "trigger": 10.00 },
        { "symbol": "FOO", "amount": 15, "trigger": 5.00 }
     ], 
     "auto_sell": [
         { "symbol": "XYZ", "amount": 12, "trigger" : 15.00 }
     ]}
```

### To directly interface with the mongo container:
- `docker-compose up -d` to get the container running in the background
- `docker exec -it mongodb bash` to run the shell inside the running mongodb container
- `mongo -u pygang_worker -p pygang_worker --authenticationDatabase pygangdb` to connect to the mongo instance
- `use pygangdb` to use the correct database
- Mongo shell commands can now be used with the same privilege as the worker container
  - `db.accounts.find()` will print out all user accounts

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