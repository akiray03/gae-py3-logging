import json
import logging
import os
import sys
import inspect

from typing import Optional
from typing import Tuple


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
            structured_log_enabled: Optional[bool] = True
    ):
        self._project_id = project_id
        self._default_logger = default_logger
        self._error_logger = error_logger
        self._trace = trace
        self._span_id = span_id
        self._structured_log_enabled = structured_log_enabled

        self._cwd = os.getcwd() + '/'

    def getLevelName(self, level) -> str:
        from logging import getLevelName
        return getLevelName(level)

    def _build_json_log_payload(self, level, msg) -> dict:
        j = {
            'Message': str(msg),
            'severity': self.getLevelName(level),
        }

        if self._trace is not None:
            j['logging.googleapis.com/trace'] = self._trace
        if self._span_id is not None:
            j['logging.googleapis.com/spanId'] = self._span_id

        caller = self.findCaller()
        if caller is not None:
            j['logging.googleapis.com/sourceLocation'] = caller

        return j

    def _json_formatter(self, d: dict) -> str:
        return json.dumps(d, ensure_ascii=False)

    def _log_text_formatter(self, d: dict) -> str:
        import datetime

        file = d.get('logging.googleapis.com/sourceLocation', {}).get('file', '<unknown>')
        file = file.replace(self._cwd, '')
        line = d.get('logging.googleapis.com/sourceLocation', {}).get('line', '-')

        msg = '[{timestamp}]{severity}:{file}:{line}: {message}'.format(
            timestamp=datetime.datetime.now(),
            severity=d.get('severity'),
            file=file,
            line=line,
            message=d.get('Message')
        )
        return msg

    def _formatter(self, d: dict) -> str:
        if self._structured_log_enabled:
            return self._json_formatter(d)
        else:
            return self._log_text_formatter(d)

    def info(self, msg, *args, **kwargs):
        level = self.INFO
        json_message = self._build_json_log_payload(
            level=level,
            msg=msg,
        )

        self._default_logger.log(level, self._formatter(json_message), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        level = self.ERROR
        json_message = self._build_json_log_payload(
            level=level,
            msg=msg,
        )

        self._error_logger.log(level, self._formatter(json_message), *args, **kwargs)

    def findCaller(self) -> Optional[dict]:
        stacks = inspect.stack()
        if len(stacks) < 4:
            return

        stack = stacks[3]

        file: str = stack.filename

        return {
            'file': file,
            'line': stack.lineno,
            'function': stack.function,
        }


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
        is_google_platform = os.environ.get('GAE_DEPLOYMENT_ID') is not None
        self._structured_log_enabled = is_google_platform

        self._default_logger, self._default_handler = self._build_logger(
            logger_name='default_logger',
            stream=sys.stdout,
            level=self.DEBUG
        )
        self._error_logger, self._error_handler = self._build_logger(
            logger_name='default_logger',
            stream=sys.stderr,
            level=self.DEBUG
        )

    @staticmethod
    def _build_logger(logger_name, stream, level) -> Tuple[logging.Logger, logging.Handler]:
        formatter = logging.Formatter('%(message)s')

        handler = logging.StreamHandler(stream=stream)
        handler.setLevel(level)
        handler.setFormatter(formatter)

        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.setLevel(level)
        if not logger.hasHandlers():
            logger.addHandler(handler)
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
            span_id=span_id,
            structured_log_enabled=self._structured_log_enabled,
        )
