import json
import logging
import os
import sys

from typing import IO
from typing import Optional
from typing import Tuple

import flask


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
