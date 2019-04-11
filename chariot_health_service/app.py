# Let's get this party started!
import falcon
from pymongo import MongoClient

import falcon_jsonify

from chariot_base.utilities import open_config_file

from chariot_base.utilities import Tracer
from chariot_health_service.resources.health import HealthResource
from wsgiref import simple_server

# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[
    falcon_jsonify.Middleware(help_messages=True),
])

opts = open_config_file()
client = MongoClient(opts.database['url'])
db = client['chariot_service_health']
options_tracer = opts.tracer

# Resources are represented by long-lived class instances
health = HealthResource(db)

if options_tracer['enabled']:
    logging.info('Enabling tracing')
    tracer = Tracer(options_tracer)
    tracer.init_tracer()
    health.inject_tracer(tracer)

app.add_route('/health', health)
app.add_route('/health/{id}', health)

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 9000, app)
    httpd.serve_forever()