from resources.cromwell import Cromwell
import flask


def test_get_version():
    app = flask.Flask(__name__)
    with app.app_context():
        assert int(Cromwell.get_version()) >= 40
