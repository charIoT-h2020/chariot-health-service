import logging

import falcon
import falcon_jsonify

from wsgiref import simple_server

from pymongo import MongoClient

from chariot_base.utilities import open_config_file
from chariot_base.utilities import Tracer
from chariot_base.datasource import LocalDataSource
from chariot_health_service import __service_name__
from chariot_health_service.resources import HealthResource, HealthLogsResource, HealthGroupsResource

# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[
    falcon_jsonify.Middleware(help_messages=True),
])

opts = open_config_file()
options_db = opts.local_storage
options_engine = opts.health
client = MongoClient(opts.database['url'])
db = client['chariot_service_health']
options_db['database'] = options_engine['database']
infux_db = LocalDataSource(**options_db)
options_tracer = opts.tracer

# Resources are represented by long-lived class instances
health = HealthResource(db)
logs = HealthLogsResource(infux_db)
availability = HealthGroupsResource(infux_db)

if options_tracer['enabled']:
    options_tracer['service'] = __service_name__
    logging.debug(f'Enabling tracing for service "{__service_name__}"')
    tracer = Tracer(options_tracer)
    tracer.init_tracer()
    health.inject_tracer(tracer)
    logs.inject_tracer(tracer)

app.add_route('/health', health)
app.add_route('/health/{id}', health)
app.add_route('/health/{id}/logs', logs)
app.add_route('/health/{id}/availability', availability)

if __name__ == '__main__':
    httpd = simple_server.make_server('0.0.0.0', 9000, app)
    httpd.serve_forever()
