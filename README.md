# MongoDB Replica Set Exporter
Prometheus exporter for mongodb replica sets

# Usage
## Building from source
 - git clone technicaljones/mongodb_replica_set_exporter
 - docker build -t mongodb_replica_set_exporter .
 - docker run -e LOG_LEVEL=DEBUG -e MONGO_URI='mongo connection uri' mongodb_replica_set_exporter

## Installing as a system service
 - Create the prometheus user on the system
 - Copy the source into /opt/prometheus
 - Copy the mongodb_replica_set_exporter.service file into /lib/systemd/system
 - systemctl daemon-reload
 - systemctl enable mongodb_replica_set_exporter.service
 - systemctl start mongodb_replica_set_exporter
 - systemctl status mongodb_replica_set_exporter

## Pulling from Docker Hub
- docker run -e LOG_LEVEL=DEBUG -e MONGO_URI='mongo connection uri' techincaljones/mongodb_replica_set_exporter

## Current Metrics
 - Replica set last commited op time
 - Replica set read concern majority op time
 - Replica set applied op time
 - Replica set durable op time
 - Replica set uptime
 - Replica set member count 
 - Replica set member state
 - Replica set member health
 - Replica set seconday lag
 - Replica set election_count

```
