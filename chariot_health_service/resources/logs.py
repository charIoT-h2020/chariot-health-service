import json
import falcon
import logging
from bson.json_util import dumps, RELAXED_JSON_OPTIONS

from chariot_base.utilities import Traceable


db_name = 'running_logs'


def build_time_filter_clause(req):
    from_date = req.get_param('from') or None
    to_date = req.get_param('to') or None

    q = []
    if from_date is not None:
        q.append('\'%s\' <= time' % from_date)
    
    if to_date is not None:
        q.append('time <= \'%s\'' % to_date)

    return q


def build_pagination_clause(req):
    page = int(req.get_param('page') or 0)
    page_size = int(req.get_param_as_int('page_size') or 10)

    return page, page_size, 'LIMIT %s OFFSET %s' % (page_size, page * page_size)


def filter_by(req, filters=[]):
    time_clause = build_time_filter_clause(req)
    page, page_size, pagination_clause= build_pagination_clause(req)

    for clause in filters:
        time_clause.insert(0, '"%s"=\'%s\'' % (clause[0], clause[1]))

    if len(time_clause) > 0:
        q = 'SELECT * FROM "health_check" WHERE %s ORDER BY time DESC %s' % (' AND '.join(time_clause), pagination_clause)
    else:
        q = 'SELECT * FROM "health_check" ORDER BY time DESC %s' % (pagination_clause)

    logging.debug('Filter by: %s' % q)
    return page, page_size, q


def group_by_time(req, aggregate, filters=[]):
    time_clause = build_time_filter_clause(req)
    interval = req.get_param('interval') or '1h'
    group_by_clause = 'GROUP BY time(%s) fill(0)' % interval

    for clause in filters:
        time_clause.insert(0, '"%s"=\'%s\'' % (clause[0], clause[1]))

    if len(time_clause) > 0:
        q = 'SELECT %s FROM "health_check" WHERE %s %s' % (' '.join(aggregate), ' AND '.join(time_clause), group_by_clause)
    else:
        q = 'SELECT %s FROM "health_check" %s' % (' '.join(aggregate), group_by_clause)

    logging.debug('Group by: %s' % q)
    return q


class HealthLogsResource(Traceable):
    def __init__(self, db):
        super(Traceable, self).__init__()
        self.tracer = None
        self.db = db

    def on_get(self, req, resp, id=None):
        span = self.start_span_from_request('get_service_health_logs', req)
        filters = []

        if id is not None:
            filters.append(['service_name', id])

        page, page_size, q = filter_by(req, filters)

        self.set_tag(span, 'q', q)
        self.set_tag(span, 'page', page)
        self.set_tag(span, 'page_size', page_size)

        results = self.db.query(q, db_name)
        results = list(results[('health_check', None)])

        resp.status = falcon.HTTP_200  # This is the default status
        resp.json = {
            'page': page,
            'size': len(results),
            'items': results
        }
        self.close_span(span)


class HealthGroupsResource(Traceable):
    def __init__(self, db):
        super(Traceable, self).__init__()
        self.tracer = None
        self.db = db

    def on_get(self, req, resp, id=None):
        span = self.start_span_from_request('get_service_health_group', req)
        filters = []

        if id is not None:
            filters.append(['service_name', id])

        groups = ['mean("running")']

        q = group_by_time(req, groups, filters)

        self.set_tag(span, 'q', q)

        results = self.db.query(q, db_name)
        results = list(results[('health_check', None)])

        resp.status = falcon.HTTP_200  # This is the default status
        resp.json = results
        self.close_span(span)