use std::{thread, time};

extern crate bollard;
extern crate lapin;

use bollard::Docker;
use lapin::{
    options::*, publisher_confirm::Confirmation, types::FieldTable, BasicProperties, Connection,
    ConnectionProperties, Result,
};

fn main() {
    #[cfg(unix)]
    Docker::connect_with_unix_defaults();

    loop {
        println!("Congratulations your application is successfully containerized with Docker!!");
        let one_second = time::Duration::from_secs(1);
        thread::sleep(one_second);
    }
}