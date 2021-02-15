db.createUser(
    {
        user : "pygang_worker",
        pwd : "pygang_worker",
        roles : [
            {
                role : "readWrite",
                db : "pygangdb"
            }
        ]
    }
)