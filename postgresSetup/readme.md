# Specify PostgreSQL custom data folder

If you want to run PostgreSQL in a VM or a Docker container in the Cloud, you may want to try different disk options to see which option performs best. Finding out how to specify and switch PostgreSQL data folder took quite bit of seaching and trial and error. Here are the steps that finally worked.

In this example, we run PostgreSQL 9.6 on Cent OS 7. PostgreSQL client can be installed using ```sudo yum install postgres```. PostgreSQL password can be stored in the user's home directory in the .pgpass file. The format should be ```hostname:port:database:username:password```, for example, ```localhost:5432:*:postgres:test_123```.

### Running PostgreSQL on a VM
1. Add a yum repo
   ```bash
   sudo yum install  https://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-7-x86_64/pgdg-redhat96-9.6-3.noarch.rpm -y
   ```
2. Install PostgreSQL server
   ```bash
   sudo yum install postgresql96 postgresql96-server postgresql96-contrib postgresql96-libs -y
   ```
3. Initialize database with default data folder
   ```bash
   sudo /usr/pgsql-9.6/bin/postgresql96-setup initdb
   ```
4. Enable PostgreSQL service
   ```bash
   sudo systemctl enable postgresql-9.6.service
   ```
5. Create custom data folder we want to use for PostgreSQL
   ```bash
   mkdir -p /pgdata
   chown -R postgres:postgres /pgdata
   ```
6. Point PGDATA to the target data folder
   ```bash
   sudo vi /etc/systemd/system/postgresql-9.6.service.d/override.conf 
   ```
   Add the following content:
   ```
   [Service]
   Environment=PGDATA=/pgdata
   ```
7. Reload daemon
   ```bash
   sudo systemctl daemon-reload
   ```
8. Initialize the database with the target data folder
   ```bash
   sudo /usr/pgsql-9.6/bin/postgresql96-setup initdb
   ```
9. Change local user login from "ident" to "trust"
   ```bash
   sudo vi /pgdata/pg_hba.conf
   ```
   Update the following lines
   ```
   # IPv4 local connections:
   host    all             all             127.0.0.1/32            trust
   # IPv6 local connections:
   host    all             all             ::1/128                 trust
   ```
10. Start PostgreSQL service
   ```bash
   sudo systemctl start postgresql-9.6.service
   # Verify PostgreSQL is pointing to the target data folder by running: 
   systemctl status postgresql-9.6.service
   ```
11. Log in to PostgreSQL as the user "postgres" and give it a password
   ```bash
   sudo -u postgres psql
   # at postgres prompt type \password
   # => \password
   # enter password
   ```
12. Restart postgres
    ```bash
    sudo systemctl restart postgresql-9.6.service
    ```
13. Run psql
    ```bash
    psql -h localhost -U postgres
    ```

### Running PostgreSQL in a Docker container
1. Install and start Docker
   ```bash
   sudo yum update -y
   sudo yum install docker
   sudo service docker start
   ```
2. Add the user to the docker group so we can run docker without sudo
   ```bash
   sudo usermod -a -G docker $(whoami)
   ```
   Log out then log in.
3. Install docker-compose
   ```bash
   sudo yum install docker-compose
   ```
4. Create the following docker-compose.yml file, assuming we want PostgreSQL to use /datadrive/pgdata as its data folder
   ```yml
   version: '3.3'

   services:

        db:
            image: postgres:9.6
            environment:
                POSTGRES_PASSWORD: postgres
                PGDATA: /opt/pgsql/data
            ports:
                - 54320:5432
            volumes:
                - /datadrive/pgdata:/opt/pgsql/data
            privileged: true
   ```
5. Run PostgreSQL Docker container
   In the folder where docker-compose.yml is in, run
   ```bash
   docker-compose up
   ```
6. Run psql
   ```bash
   psql -h localhost -p 54320 -U postgres
   ```
