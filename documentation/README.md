# Pygang - Group 3

Documentation for the January 31st milestone.

## Initial Requirements

All requirements are pulled from CourseProject.pdf.

* The system must include a prototype mobile client application which provides a user interface to the system's backend day trading system as well as a **local store** of the current state of the given users account information.
* The front-end website will be used by the course tutorial instructor to test and interact with each team's operational system.
* All transactions within the system must be logged. The log files must follow the format outlined by logfile.xsd.
* The server code for the project must be run on the Linux lab B203 machines
  * These machines are at the addresses b130.seng.uvic.ca through b150.seng.uvic.ca
  * No part of the project may run on machines in B215 or B220
* NOTE: Section 7 "Project Planning and Work Effort" in CourseProject.pdf notes that our project website needs to track our group progress, including transaction processing speeds. It goes on to say this portion of the website consists of a public portion that includes tracking the milestones at a daily level, and a private portion of the website may be used to track documentaion and development efforts in more detail. I (Oliver) can only assume this is referring to our GitHub repo and not the actual front-end of our website.  
* Docker Container technologies must be used.
* The system must interface with the legacy code server.

#### Functionality

* The centralised transaction processing system must support a large number of remote clients. Clients will log in through a web browser to perform stock trading and account management, such as:
  * View their account
  * Add money to their account
  * Get a stock quote
  * Buy a number of shares in a stock
  *  Sell a number of shares in a stock they own
  * Set an automated sell point for a stock
  * Set an automated buy point for a stock
  * Review their complete list of transactions
  * Cancel a specified transaction prior to it being committed
  * Commit a transaction.
* The client activities outlined above must be logged and available on command. Details include: all transactions (including timestamps), a record of each individual transaction, processing time information, and all account state changes within the system. This must be dumped as a ASCII text file with the DUMPLOG command.
* A complete set of all commands, as well as syntax, can be found in Appendix A and Commands.html.

#### Architecture Goals

* Minimum transaction processing times
* Full support for required features
* Reliability and maintainability of the system
* High availability and fault recovery (i.e. proper use of fault tolerance)
* Minimal costs (development, hardware, maintenance, etc.)
* Clean design that is easily understandable and maintainable
* Appropriate security
* Clean web-client interface

## Programming Tools & Libraries

- Python3
- uWSGI
- Flask
- NginX

## Development Platform



## Architecture



### Schema

Not sure what "schema" is referring to - Oliver

### UML

## Project Plan

## Task Assignment