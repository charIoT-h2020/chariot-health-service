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
        self.status = {}

    def set_up_local_storage(self, options):
        self.datastore = open_datasource(options)

    def inject_dispatcher(self, dispatcher):
        self.dispatcher = dispatcher

    def on_message(self, client, topic, payload, qos, properties):
        msg = payload.decode('utf-8')
        deserialized_model = json.loads(msg)
        self.status[deserialized_model['name']] = None
        self.health_check_result(deserialized_model)

    async def send_ping(self):
        for service in self.services:
            if service['protocol'] == 'mqtt':
                await self.check_for_failed_request(service)

                package_id = str(uuid.uuid4())
                health_package = {
                    'id': package_id,
                    'destination': 'health/_callback',
                    'timestamp': datetime.datetime.utcnow().isoformat()
                }
                self.publish(service['endpoint'], json.dumps(health_package))

                self.datastore.publish_dict({
                    'table': 'send_check',
                    'tags': {
                        'service_name': service['name']
                    },
                    'timestamp': health_package['timestamp'],
                    'message': health_package
                })

                self.status[service['name']] = {
                    'id': package_id,
                    'answer': False
                }

    async def check_for_failed_request(self, service):
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

    def health_check_result(self, deserialized_model):
        diff = dateutil.parser.parse(
            deserialized_model['received']) - dateutil.parser.parse(deserialized_model['sended'])

        running = 1 if deserialized_model['status']['code'] == 0 else 0

        self.datastore.publish_dict({
            'table': 'health_check',
            'tags': {
                'service_name': deserialized_model['name']
            },
            'timestamp': deserialized_model['sended'],
            'message': {
                'id': deserialized_model['id'],
                'service_name': deserialized_model['name'],
                'sended': deserialized_model['sended'],
                'received': deserialized_model['received'],
                'time_spent': diff.total_seconds(),
                'running': running,
            }
        })


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
