# -*- coding: utf-8 -*-

import os
import uuid
import json
import time
import gmqtt
import signal
import asyncio
import logging
import datetime
from pymongo import MongoClient
import dateutil.parser

from pytz import utc

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from chariot_base.utilities import open_config_file, Tracer
from chariot_base.datasource import open_datasource
from chariot_base.connector import LocalConnector, create_client


class SouthboundConnector(LocalConnector):
    def __init__(self, options):
        super(SouthboundConnector, self).__init__()
        self.dispatcher = None
        self.datastore = None
        self.services = options['services']
        self.db = None
        self.status = {}

    def set_up_local_storage(self, options):
        self.datastore = open_datasource(options)

    def inject_db(self, db):
        self.db = db

    def on_message(self, client, topic, payload, qos, properties):
        msg = payload.decode('utf-8')
        deserialized_model = json.loads(msg)
        self.status[deserialized_model['name']] = None
        self.health_check_result(deserialized_model)
        self.save_succeess_to_database(deserialized_model)

    def save_succeess_to_database(self, package):
        diff = dateutil.parser.parse(
            package['received']) - dateutil.parser.parse(package['sended'])

        service = self.db.service.find_one({'name': package['name']})
        running = 1 if package['status']['code'] == 0 else 0

        if service is None:
            logging.debug('save')
            self.db.subscribers.save({
                "name": package['name'],
                "status": package['status'],
                "received": package['sended'], 
                "sended": package['received'],
                "package_id": package['id'],
                "request_stats": {
                    "success": running,
                    "total": 1
                }
            })
        else:
            logging.debug('update')
            self.db.subscribers.update(subscriber, { 
                "$set": { 
                    "status": package['status'],
                    "received": package['sended'], 
                    "sended": package['received'],
                    "package_id": package['id'],
                    "request_stats": {
                        "success": subscriber['request_stats']['success'] + running,
                        "total": subscriber['request_stats']['total'] + 1
                    }
                } 
            })

    def health_check_result(self, package):
        diff = dateutil.parser.parse(
            package['received']) - dateutil.parser.parse(package['sended'])

        running = 1 if package['status']['code'] == 0 else 0

        self.datastore.publish_dict({
            'table': 'health_check',
            'tags': {
                'service_name': package['name']
            },
            'timestamp': package['sended'],
            'message': {
                'id': package['id'],
                'service_name': package['name'],
                'sended': package['sended'],
                'received': package['received'],
                'time_spent': diff.total_seconds(),
                'running': running,
            }
        })

    async def send_ping(self):
        for service in self.services:
            if service['protocol'] == 'mqtt':
                previous_status = await self.check_for_failed_request(service)

                health_package = {
                    'id': str(uuid.uuid4()),
                    'destination': 'health/_callback',
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
                self.publish(service['endpoint'], json.dumps(health_package))

                await self.save_send_check(service, health_package)
                await self.save_to_database(service, health_package, previous_status)

                self.status[service['name']] = {
                    'id': health_package['id'],
                    'answer': False,
                    'sended': health_package['timestamp']
                }
    

    async def save_to_database(self, service, health_package, previous_status):
        pass

    async def save_send_check(self, service, health_package):
        self.datastore.publish_dict({
            'table': 'send_check',
            'tags': {
                'service_name': service['name']
            },
            'timestamp': health_package['timestamp'],
            'message': health_package
        })

    async def check_for_failed_request(self, service):
        service = self.db.service.find_one({'name': service['name']})

        previus_req = self.status.get(service['name'], None)
        if previus_req is not None:
            self.datastore.publish_dict({
                'table': 'health_check',
                'tags': {
                    'service_name': service['name']
                },
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'message': {
                    'id': previus_req['id'],
                    'service_name': service['name'],
                    'running': 0
                }
            })
            self.status[service['name']] = None
            return False
        return True


STOP = asyncio.Event()


def ask_exit(*args):
    logging.info('Stoping....')
    STOP.set()


async def main(args=None):

    opts = open_config_file()

    options_db = opts.local_storage
    options_engine = opts.health
    options_tracer = opts.tracer

    scheduler = AsyncIOScheduler(timezone=utc)
    client = MongoClient(opts.database['url'])
    db = client['chariot_service_health']

    southbound = SouthboundConnector(options_engine)
    if options_tracer['enabled'] is True:
        logging.info('Enabling tracing')
        tracer = Tracer(options_tracer)
        tracer.init_tracer()
        southbound.inject_tracer(logger.tracer)
    southbound.set_up_local_storage(options_db)
    client_south = await create_client(opts.brokers.southbound)
    southbound.register_for_client(client_south)
    southbound.inject_db(db)
    await southbound.send_ping()
    scheduler.add_job(southbound.send_ping,
                      'interval', seconds=options_engine['interval'])
    southbound.subscribe(options_engine['listen'], qos=2)
    scheduler.start()

    logging.info('Waiting message for health checking')
    await STOP.wait()
    await client_south.disconnect()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    loop.run_until_complete(main())
    logging.info('Stopped....')
