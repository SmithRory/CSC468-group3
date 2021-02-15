use std::{thread, time};

fn main() {
    loop {
        println!("Congratulations your application is successfully containerized with Docker!!");
        let one_second = time::Duration::from_secs(1);
        thread::sleep(one_second);
    }
}