import json
import falcon
import logging
from bson.json_util import dumps, RELAXED_JSON_OPTIONS

from chariot_base.utilities import Traceable


# -*- coding: utf-8 -*-


class HealthResource(Traceable):
    def __init__(self, db):
        super(Traceable, self).__init__()
        self.tracer = None
        self.db = db

    def on_get(self, req, resp, id=None):
        span = self.start_span_from_request('get_service_health_info', req)
        if id is None:
            result = self.db.services.find() or []
        else:
            self.set_tag(span, 'name', id)
            print(id)
            result = self.db.services.find_one({'name': id.lower()})

        resp.body = dumps(result, json_options=RELAXED_JSON_OPTIONS)
        self.close_span(span)
