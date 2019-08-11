import json
import logging
import os
import sys

from typing import IO
from typing import Optional
from typing import Tuple

import flask


class CustomLogger:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    FATAL = logging.FATAL
    CRITICAL = logging.CRITICAL

    def __init__(
            self,
            project_id: str,
            default_logger: logging.Logger,
            error_logger: logging.Logger,
            trace: Optional[str] = None,
            span_id: Optional[str] = None,
    ):
        self._project_id = project_id
        self._default_logger = default_logger
        self._error_logger = error_logger
        self._trace = trace
        self._span_id = span_id

    def getLevelName(self, level) -> str:
        from logging import getLevelName
        return getLevelName(level)

    def _build_json_log_payload(self, level, msg) -> dict:
        return {
            'Message': str(msg),
            'severity': self.getLevelName(level),
            'logging.googleapis.com/trace': self._trace,
            'logging.googleapis.com/spanId': self._span_id,
            'logging.googleapis.com/sourceLocation': {
                'file': __file__,
                'line': 47,
                'function': str(__name__)
            }
        }

    def _safety_json_dumps(self, d: dict) -> str:
        return json.dumps(d)

    def info(self, msg, *args, **kwargs):
        level = self.INFO
        json_message = self._build_json_log_payload(
            level=level,
            msg=msg,
        )

        self._default_logger.log(level, self._safety_json_dumps(json_message), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        level = self.ERROR
        json_message = self._build_json_log_payload(
            level=level,
            msg=msg,
        )

        self._error_logger.log(level, self._safety_json_dumps(json_message), *args, **kwargs)

    def findCaller(self):
        pass


class CustomLoggerManager:
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    FATAL = logging.FATAL
    CRITICAL = logging.CRITICAL

    def __init__(
            self,
    ):
        self._project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', '<unknown-project>')

        self._default_logger, self._default_handler = self._build_logger(
            logger_name='default_logger',
            stream=sys.stdout,
            level=self.DEBUG
        )
        self._error_logger, self._error_handler = self._build_logger(
            logger_name='default_logger',
            stream=sys.stdout,
            level=self.DEBUG
        )

    @staticmethod
    def _build_logger(logger_name, stream, level) -> Tuple[logging.Logger, logging.Handler]:
        formatter = logging.Formatter('%(message)s')

        handler = logging.StreamHandler()
        handler.setStream(stream)
        handler.setLevel(level)
        handler.setFormatter(formatter)

        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.addHandler(handler)
        logger.setLevel(level)
        return (logger, handler)

    def getLevelName(self, level) -> str:
        from logging import getLevelName
        return getLevelName(level)

    def flush(self):
        self._default_handler.flush()
        self._error_handler.flush()

    def _build_trace_and_span(self, trace_header: str) -> Tuple[Optional[str], Optional[str]]:
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

    def getLogger(self, trace_header: Optional[str] = None) -> CustomLogger:
        trace, span_id = self._build_trace_and_span(trace_header)

        return CustomLogger(
            project_id=self._project_id,
            default_logger=self._default_logger,
            error_logger=self._error_logger,
            trace=trace,
            span_id=span_id
        )
