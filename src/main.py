import flask
import time
import logging
import sys
import os
import time
import json

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = flask.Flask('app')


@app.route('/')
def root():
    return 'Hello, world'


@app.route('/sleep')
def sleep():
    trace_id = flask.request.headers.get('X-Cloud-Trace-Context')

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
            'Message': f'Sleep {i}',
            'severity': 'DEFAULT',
            'logging.googleapis.com/trace': trace_id,
        }
        print(json.dumps(j))
        logger.debug(f'sleep {i}')

    return 'sleep and wakeup.'


if __name__ == '__main__':
    app.run(port=8080, debug=True)
