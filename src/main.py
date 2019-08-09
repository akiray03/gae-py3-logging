import flask
import time
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = flask.Flask('app')


@app.route('/')
def root():
    return 'Hello, world'


@app.route('/sleep')
def sleep():
    for i in range(0, 10):
        time.sleep(1)
        logger.debug(f'sleep {i}')

    return 'sleep and wakeup.'


if __name__ == '__main__':
    app.run(port=8080, debug=True)
