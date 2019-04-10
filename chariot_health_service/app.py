# Let's get this party started!
import falcon
from pymongo import MongoClient

import falcon_jsonify

from chariot_base.utilities import open_config_file

from chariot_base.utilities import Tracer
from chariot_subscribe_service.resources.subscriber import SubscriberResource
from wsgiref import simple_server

# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[
    falcon_jsonify.Middleware(help_messages=True),
])

opts = open_config_file()
client = MongoClient(opts.database['url'])
db = client['chariot_subscribe_service']
options_tracer = opts.tracer

# Resources are represented by long-lived class instances
subscriber = SubscriberResource(db)

if options_tracer['enabled']:
    tracer = Tracer(options_tracer)
    tracer.init_tracer()
    subscriber.inject_tracer(tracer)

app.add_route('/subscriber', subscriber)
app.add_route('/subscriber/{id}', subscriber)
app.add_route('/subscriber/{id}/{sensor_id}', subscriber)

if __name__ == '__main__':
    httpd = simple_server.make_server('127.0.0.1', 9000, app)
    httpd.serve_forever()