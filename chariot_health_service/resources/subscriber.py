import json
import falcon
import logging
from bson.json_util import dumps, RELAXED_JSON_OPTIONS

from chariot_base.utilities import Traceable


# -*- coding: utf-8 -*-


class SubscriberResource(Traceable):
    def __init__(self, db):
        super(Traceable, self).__init__()
        self.tracer = None
        self.db = db

    def on_get(self, req, resp, id=None):
        span = self.start_span_from_request('get_subscriber', req)
        if id is None:
            result = self.db.subscribers.find()
        else:
            self.set_tag(span, 'id', id)
            result = self.db.subscribers.find_one({'id': id.lower()})

        resp.body = dumps(result, json_options=RELAXED_JSON_OPTIONS)
        self.close_span(span)

    def on_delete(self, req, resp, id, sensor_id=None):
        try:
            span = self.start_span_from_request('get_subscriber', req)
            id = id.lower()
            result = {
                'id': id
            }
            if sensor_id is None:
                status = self.db.subscribers.delete_one({'id': id})
                result['action'] = 'remove_subscriber'
                result['status'] = status.deleted_count > 0
            else:
                sensor_id = sensor_id.lower()
                subscriber = self.db.subscribers.find_one({'id': id})
                status = self.db.subscribers.update(subscriber, { "$pull": { "sensors": sensor_id } } )
                result['action'] = 'remove_sensor'
                result['sensor_id'] = sensor_id
                result['status'] = status['nModified'] > 0


            resp.json = result
            self.log(span, result)
            self.close_span(span)
        except Exception as ex:
            self.error(span, ex)
            raise

    def on_put(self, req, resp):
        self.create_or_update(req, resp)

    def on_post(self, req, resp):
        self.create_or_update(req, resp)

    def create_or_update(self, req, resp):
        span = self.start_span_from_request('edit_subscriber', req)
        subscriber_id = req.get_json('subscriber_id').lower()
        sensor_ids = [sensor_id.lower() for sensor_id in req.get_json('sensor_ids')]

        subscriber = self.db.subscribers.find_one({'id': subscriber_id})
        if subscriber is None:
            self.set_tag(span, 'updated', False)
            subscriber = {
                'id': subscriber_id,
                'sensors': sensor_ids
            }
            result = self.db.subscribers.save(subscriber)
        else:
            self.set_tag(span, 'updated', True)
            result = self.db.subscribers.update(subscriber, { "$addToSet": { "sensors": sensor_ids } } )

        resp.body = dumps(result, json_options=RELAXED_JSON_OPTIONS)
        self.close_span(span)