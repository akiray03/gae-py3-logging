import flask
import time
import logging
import sys
import os
import json
import traceback
import datetime
import uuid

from gumo.logging import CustomLoggerManager

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

my_gae_log_path = '/var/log/my-gae-log' if 'GAE_DEPLOYMENT_ID' in os.environ else 'log/my-gae-log'
if not os.path.exists(os.path.dirname(my_gae_log_path)):
    os.makedirs(os.path.dirname(my_gae_log_path))
handler = logging.FileHandler(filename=my_gae_log_path)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(message)s'))
gae_logger = logging.getLogger('my_gae_logger')
gae_logger.propagate = False
gae_logger.addHandler(handler)
gae_logger.setLevel(logging.DEBUG)

app = flask.Flask('app')


custom_logger_manager = CustomLoggerManager()

@app.before_request
def on_before_request():
    flask.g.custom_logger = custom_logger_manager.getLogger(
        trace_header=flask.request.headers.get('X-Cloud-Trace-Context')
    )

@app.after_request
def on_after_request(response):
    custom_logger_manager.flush()
    return response


@app.route('/')
def root():
    logger.info(f'headers:\n{flask.request.headers}')
    return 'Hello, world'


@app.route('/gae_log')
def gae_log():
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', '<unknown-project>')
    app_id = f'b~{project_id}'

    trace_header = flask.request.headers.get('X-Cloud-Trace-Context')

    trace_id = None
    span_id = None

    if trace_header is not None and trace_header.find('/') >= 0:
        trace_id, span_id = trace_header.split('/', )
        if span_id.find(';') >= 0:
            span_id = span_id.split(';')[0]

    trace = f'projects/{project_id}/traces/{trace_id}'

    now = datetime.datetime.utcnow()
    start_time = now - datetime.timedelta(seconds=2)
    end_time = now + datetime.timedelta(seconds=3)

    j = {
        '@type': 'type.googleapis.com/google.appengine.logging.v1.RequestLog',
        # 'appEngineRelease': '1.9.71',  # TODO
        'appId': app_id,
        'cost': 0.0,
        'endTime': end_time.isoformat(),
        'finished': True,
        'first': True,
        'host': flask.request.host,
        'httpVersion': 'HTTP/1.1',  # TODO
        'instanceId': os.environ.get('GAE_INSTANCE'),
        'instanceIndex': -1,
        'ip': flask.request.headers.get('X-Appengine-User-Ip', flask.request.remote_addr),
        'latency': '0.0s',
        'line': [
            {
                'logMessage': 'This is request message',
                'severity': 'INFO',
                'time': start_time.isoformat(),
                'sourceLocation': {
                    'file': __file__,
                    'line': 47,
                    'function': str(__name__)
                }
            },
            {
                'logMessage': 'This is request message :smile:',
                'severity': 'DEBUG',
                'time': now.isoformat(),
                'sourceLocation': {
                    'file': __file__,
                    'line': 47,
                    'function': str(__name__)
                }
            },
        ],
        'megaCycles': '0',
        'method': flask.request.method,
        'requestId': os.environ.get('X-Appengine-Request-Log-Id', str(uuid.uuid4())),
        'resource': flask.request.path,
        'startTime': start_time.isoformat(),
        'status': 200,  # TODO
        'traceId': trace_id,
        'traceSampled': True,
        'urlMapEntry': 'auto',
        'userAgent': str(flask.request.user_agent),
        'versionId': os.environ.get('GAE_VERSION'),
        'wasLoadingRequest': False,  # TODO

        'severity': 'INFO',
        'logging.googleapis.com/trace': trace,
        'logging.googleapis.com/spanId': span_id,
        # 'logging.googleapis.com/sourceLocation': {
        #     'file': __file__,
        #     'line': 47,
        #     'function': str(__name__)
        # }
    }

    j2 = {
        'Message': 'this is child log message',
        'severity': 'INFO',
        'logging.googleapis.com/trace': trace,
        'logging.googleapis.com/spanId': span_id,
        'logging.googleapis.com/sourceLocation': {
            'file': __file__,
            'line': 47,
            'function': str(__name__)
        }
    }

    gae_logger.info(json.dumps(j))
    print(json.dumps(j2), flush=True)

    return flask.jsonify(j)


@app.route('/logging')
def logging():
    flask.g.custom_logger.info('Hello test message 日本語エラーメッセージ')
    flask.g.custom_logger.error('Hello. this is error test message')
    flask.g.custom_logger.exception('Hello. this is error test message')

    try:
        1 / 0
    except Exception as e:
        flask.g.custom_logger.exception(e)

    return 'Hi.'


@app.route('/sleep')
def sleep():
    cloud_trace_context = flask.request.headers.get('X-Cloud-Trace-Context')
    logger.debug(f'X-Cloud-Trace-Context = {cloud_trace_context}')
    trace_id = None
    span_id = None
    if cloud_trace_context.find('/') >= 0:
        trace_id, span_id = cloud_trace_context.split('/', )
        if span_id.find(';') >= 0:
            span_id = span_id.split(';')[0]

    project_name = os.environ.get('GOOGLE_CLOUD_PROJECT', '<project-id>')
    trace = f'projects/{project_name}/traces/{trace_id}'
    logger.debug(f'trace = {trace}, span_id = {span_id}')

    for i in range(0, 10):
        time.sleep(1)
        # Output:
        # {
        #     "Message": "Hi!",
        #     "severity": "DEFAULT",
        #     "time": "2019-05-18T13:47:00Z",
        #     "logging.googleapis.com/trace": "projects/foobar/traces/65ed3bb1ceb342ba0ca62fa64076c738",
        #     "logging.googleapis.com/spanId": "2325d572b51a4ba6",
        #     "logging.googleapis.com/sourceLocation": {
        #         "file": "/tmp/123456/sdlog/buildlog/example_test.go",
        #         "line": "55",
        #         "function": "github.com/vvakame/sdlog/buildlog_test.Example_emitJSONPayloadWithEmbed"
        #     }
        # }

        j = {
            'Message': f'Sleep {i}; {trace}, {span_id}',
            'severity': 'DEFAULT',
            'logging.googleapis.com/trace': trace,
            'logging.googleapis.com/spanId': span_id,
            'logging.googleapis.com/sourceLocation': {
                'file': __file__,
                'line': 47,
                'function': str(__name__)
            }
        }
        print(json.dumps(j))
        logger.debug(f'sleep {i}; {json.dumps(j)}')

    j = {
        'severity': 'DEFAULT',
        'logging.googleapis.com/trace': trace,
        'logging.googleapis.com/spanId': span_id,
        'logging.googleapis.com/sourceLocation': {
            'file': __file__,
            'line': 47,
            'function': str(__name__)
        }
    }

    try:
        raise RuntimeError('this is error!')
    except Exception as e:
        j['Message'] = str(e) + '\n' + traceback.format_exc()
        print(json.dumps(j), file=sys.stderr)

    return 'sleep and wakeup.'


if __name__ == '__main__':
    app.run(port=8080, debug=True)
