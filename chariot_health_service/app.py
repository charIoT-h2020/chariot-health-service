# Let's get this party started!
import falcon
from pymongo import MongoClient

import falcon_jsonify

from chariot_base.utilities import open_config_file

from chariot_base.utilities import Tracer
from chariot_base.datasource import LocalDataSource
from chariot_health_service.resources import HealthResource, HealthLogsResource, HealthGroupsResource
from wsgiref import simple_server

# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[
    falcon_jsonify.Middleware(help_messages=True),
])

opts = open_config_file()
options_db = opts.local_storage
client = MongoClient(opts.database['url'])
db = client['chariot_service_health']
infux_db = LocalDataSource(options_db['host'], options_db['port'],
                           options_db['username'], options_db['password'], options_db['database'])
options_tracer = opts.tracer

# Resources are represented by long-lived class instances
health = HealthResource(db)
logs = HealthLogsResource(infux_db)
availability = HealthGroupsResource(infux_db)

if options_tracer['enabled']:
    logging.info('Enabling tracing')
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
