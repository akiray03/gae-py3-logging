import flask
import time
import logging
import sys
import os
import time
import json
import traceback

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = flask.Flask('app')


@app.route('/')
def root():
    return 'Hello, world'


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
        try:
            raise RuntimeError('this is error!')
        except Exception as e:
            j['Message'] = str(e) + '\n' + traceback.format_exc()

            print(json.dumps(j), file=sys.stderr)
        logger.debug(f'sleep {i}; {json.dumps(j)}')

    return 'sleep and wakeup.'


if __name__ == '__main__':
    app.run(port=8080, debug=True)
