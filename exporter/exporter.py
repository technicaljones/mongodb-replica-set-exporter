#!/usr/bin/python
# -*- coding: UTF-8 -*-

'''
Imports
'''
# General
import os
import logging
import time
import json

# Mongo
from pymongo import MongoClient
import bson
import pymongo.errors
from bson.json_util import dumps


# Prometheus
from prometheus_client import start_http_server, REGISTRY
from prometheus_client.core import GaugeMetricFamily

exporter_port = 8000

mongo_config = {
            'uri': os.environ.get('MONGO_URI')
        }

log_level = os.environ.get('LOG_LEVEL', 'INFO')

logging.basicConfig(level=log_level)


class MongoDbCollector(object):
    def __init__(self, mongodb_connection):

        self.connection = mongodb_connection
        self.metrics = {}

    def collect(self):
        self.metrics = {
            'replica_set_last_committed_optime_seconds': GaugeMetricFamily(
                'replica_set_last_committed_optime_seconds',
                'Replica set last commited op time',
                labels=[]),
            'replica_set_read_concern_majority_optime_seconds': GaugeMetricFamily(
                'replica_set_read_concern_majority_optime_seconds',
                'Replica set read concern majority op time',
                labels=[]),
            'replica_set_applied_optime_seconds': GaugeMetricFamily(
                'replica_set_applied_optime_seconds',
                'Replica set applied op time',
                labels=[]),
            'replica_set_durable_optime_seconds': GaugeMetricFamily(
                'replica_set_durable_optime_seconds',
                'Replica set durable op time',
                labels=[]),
            'replica_set_uptime_seconds': GaugeMetricFamily(
                'replica_set_uptime_seconds',
                'Replica set uptime',
                labels=['member_name']),
            'replica_set_member_count': GaugeMetricFamily(
                'replica_set_member_count',
                'Replica set member count',
                labels=['health']),
            'replica_set_member_states': GaugeMetricFamily(
                'replica_set_member_state',
                'Replica set member state',
                labels=['member_name']),
            'replica_set_member_health': GaugeMetricFamily(
                'replica_set_member_health',
                'Replica set member health',
                labels=['member_name']),
            'replica_set_secondary_lag_seconds': GaugeMetricFamily(
                'replica_set_secondary_lag_seconds',
                'Replica set seconday lag',
                labels=['member_name']),
            'replica_set_election_count': GaugeMetricFamily(
                'replica_set_election_count',
                'Replica set election_count',
                labels=[])
        }

        if self.check_replica_set():

            self.get_replica_set_metrics()

        for metric_name, metric in self.metrics.items():
            logging.debug('-- Yielding metric: {0}'.format(metric_name))
            yield metric

    def check_replica_set(self):
        replica_set = False

        rs_status = self.connection.admin.command('replSetGetStatus')

        if rs_status['ok'] == 1:
            replica_set = True

        return replica_set

    def get_replica_set_metrics(self):

        replica_set = self.connection.admin.command('replSetGetStatus')

        self.optime_metrics(replica_set)

        self.replica_set_member_uptime_metrics(replica_set)

        self.replica_set_member_states(replica_set)

        self.replica_set_member_health(replica_set)

        self.replica_set_member_count(replica_set)

        self.replica_set_secondary_lag(replica_set)

        self.replica_set_election_count(replica_set)

    def optime_metrics(self, replica_set):

        optimes = replica_set['optimes']

        self.metrics['replica_set_last_committed_optime_seconds'].add_metric(
            'replica_set_last_committed_optime',
            self.decode_bson_timestamp(optimes['lastCommittedOpTime']['ts'])
        )
        self.metrics['replica_set_read_concern_majority_optime_seconds'].add_metric(
            'replica_set_read_concern_majority_optime',
            self.decode_bson_timestamp(optimes['readConcernMajorityOpTime']['ts'])
        )
        self.metrics['replica_set_applied_optime_seconds'].add_metric(
            'replica_set_read_concern_majority_optime',
            self.decode_bson_timestamp(optimes['appliedOpTime']['ts'])
        )
        self.metrics['replica_set_durable_optime_seconds'].add_metric(
            'replica_set_durable_optime',
            self.decode_bson_timestamp(optimes['durableOpTime']['ts'])
        )

    def replica_set_member_uptime_metrics(self, replica_set):

        for member in replica_set['members']:

            self.metrics['replica_set_uptime_seconds'].add_metric(
                [member['name']],
                member['uptime']
            )

    def replica_set_member_states(self, replica_set):

        for member in replica_set['members']:

            self.metrics['replica_set_member_states'].add_metric(
                [member['name']],
                member['state']
            )

    def replica_set_member_health(self, replica_set):

        for member in replica_set['members']:

            self.metrics['replica_set_member_health'].add_metric(
                [member['name']],
                member['health']
            )

    def replica_set_member_count(self, replica_set):

        self.metrics['replica_set_member_count'].add_metric(
            ['all'],
            len(replica_set['members'])
        )

        healthy_count = 0
        unhealthy_count = 0

        for member in replica_set['members']:
            if member['health'] == 1:
                healthy_count += 1
            else:
                unhealthy_count += 1

        self.metrics['replica_set_member_count'].add_metric(
            ['healthy_count'],
            healthy_count
        )

        self.metrics['replica_set_member_count'].add_metric(
            ['unhealthy_count'],
            unhealthy_count
        )

    def replica_set_secondary_lag(self, replica_set):

        # Get primary optime
        primary_optime = 0

        for member in replica_set['members']:
            if member['state'] == 1:
                primary_optime = member['optimeDate']
                break

        # Calculate lag in seconds for each secondary
        for member in replica_set['members']:
            if member['state'] in [2, 3]:
                secondary_optime = member['optimeDate']
                lag = (primary_optime - secondary_optime).total_seconds()

                self.metrics['replica_set_secondary_lag_seconds'].add_metric(
                    [member['name']],
                    lag
                )

    def replica_set_election_count(self, replica_set):

        self.metrics['replica_set_election_count'].add_metric(
            'replica_set_election_count',
            float(bson.json_util.dumps(replica_set['term']))
        )


    def decode_bson_timestamp(self, timestamp):
        return json.loads(bson.json_util.dumps(timestamp))['$timestamp']['t']


def connect():
    logging.info('-- Mongo URI: {0}'.format(mongo_config['uri']))
    logging.info('-' * 50)
    client = MongoClient(mongo_config['uri'])

    try:
        client.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        logging.error('Unable to connect to MongoDB')
        client = None

    return client


if __name__ == '__main__':
    logging.info('-- Starting exporter')
    logging.info('-- Exporter port: {0}'.format(exporter_port))
    logging.info('-' * 50)

    start_http_server(exporter_port)
    connection = connect()
    if connection:
        REGISTRY.register(MongoDbCollector(connection))
        logging.info('-- Listening...')
        while True:
            time.sleep(1)
    else:
        logging.error('No Mongo Connection')
