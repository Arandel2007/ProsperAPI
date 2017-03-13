"""manager.py: Flask-Script launcher for services

using https://github.com/yabb85/ueki as prototype
"""
from os import path

from flask_script import Manager, Server

from prosper.publicAPI import create_app

HERE = path.abspath(path.dirname(__file__))
ROOT = path.dirname(HERE)

SETTINGS = {
    'PORT':8001
}
app = create_app(SETTINGS)

manager = Manager(app)
manager.add_command(
    'runserver',
    Server(
        host='0.0.0.0',
        port=SETTINGS['PORT']
    )
)
manager.add_command(
    'debug',
    Server(
        host='localhost',
        port=SETTINGS['PORT']
    )
)

if __name__ == '__main__':
    manager.run()
