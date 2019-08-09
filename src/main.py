import flask


app = flask.Flask('app')


@app.route('/')
def root():
    return 'Hello, world'


if __name__ == '__main__':
    app.run(port=8080, debug=True)
