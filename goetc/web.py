from flask import Flask, render_template

from goetc.config import CONFIG, DATA

app = Flask(__name__)


# init config
CONFIG.init()


@app.route('/')
def hello_world():
    return app.send_static_file('index.html')


@app.route('/config')
def config():
    return {
        'bandpasses': CONFIG.recursive_groups(DATA.BANDPASS),
        'telescopes': CONFIG.groups(DATA.TELESCOPE),
        'cameras': CONFIG.groups(DATA.CAMERA),
        'qes': CONFIG.groups(DATA.QE),
        'templates': CONFIG.groups(DATA.SPECTRUM)
    }


@app.route('/telescope/<string:name>')
def telescope(name):
    return CONFIG.telescope_config(name)


@app.route('/camera/<string:name>')
def camera(name):
    return CONFIG.camera_config(name)
