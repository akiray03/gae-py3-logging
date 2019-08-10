import flask
import time
import logging
import sys
import os
import json
import traceback

from typing import IO
from typing import Optional
from typing import Tuple

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = flask.Flask('app')


class CustomLogger:
    INFO = logging.INFO

    def __init__(
            self,
            level: int = logging.NOTSET,
            default_stream: Optional[IO] = None,
            error_stream: Optional[IO] = None,
    ):
        self._project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', '<unknown-project>')

        self._level = level
        self._default_stream = default_stream or sys.stdout
        self._error_stream = error_stream or sys.stderr

        self._default_logger = self._build_logger(
            logger_name='default_logger',
            stream=self._default_stream,
            level=self._level,
        )
        self._error_logger = self._build_logger(
            logger_name='error_logger',
            stream=self._error_stream,
            level=self._level,
        )

    @staticmethod
    def _build_logger(logger_name, stream, level) -> logging.Logger:
        formatter = logging.Formatter('%(message)s')

        handler = logging.StreamHandler()
        handler.setStream(stream)
        handler.setLevel(level)
        handler.setFormatter(formatter)

        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(level)
        return logger

    def _get_level_name(self, level) -> str:
        from logging import getLevelName
        return getLevelName(level)

    def get_trace_header(self) -> Optional[str]:
        # TODO: 外部から登録できるようにする
        return flask.request.headers.get('X-Cloud-Trace-Context')

    def _build_trace_and_span(self) -> Tuple[Optional[str], Optional[str]]:
        trace_header = self.get_trace_header()
        if trace_header is None:
            return (None, None)

        trace_id = None
        span_id = None

        if trace_header.find('/') >= 0:
            trace_id, span_id = trace_header.split('/', )
            if span_id.find(';') >= 0:
                span_id = span_id.split(';')[0]

        trace = f'projects/{self._project_id}/traces/{trace_id}'

        return (trace, span_id)

    def _build_json_log_payload(self, level, msg) -> dict:
        trace, span_id = self._build_trace_and_span()

        return {
            'Message': msg,
            'severity': self._get_level_name(level),
            'logging.googleapis.com/trace': trace,
            'logging.googleapis.com/spanId': span_id,
            'logging.googleapis.com/sourceLocation': {
                'file': __file__,
                'line': 47,
                'function': str(__name__)
            }
        }

    def _safety_json_dumps(self, d: dict) -> str:
        # TODO: シリアライズ不可能なオブジェクトの場合も、良い感じに処理しつつ、エラーにならないようにする
        return json.dumps(d)

    def info(self, msg, *args, **kwargs):
        level = self.INFO
        json_message = self._build_json_log_payload(
            level=level,
            msg=msg,
        )

        self._default_logger.log(level, self._safety_json_dumps(json_message), *args, **kwargs)

    def findCaller(self):
        pass


custom_logger = CustomLogger()


@app.route('/')
def root():
    return 'Hello, world'


@app.route('/logging')
def logging():
    custom_logger.info('Hello test message')
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
