from flask_restplus import Resource, Namespace, reqparse
from resources._logger import *
from schemas.study_node_schema import StudyNodeSchema
from schemas.user_node_schema import UserNodeSchema
from schemas.added_by_rel_schema import AddedByRelSchema
import marshmallow.exceptions
from werkzeug.exceptions import BadRequest
from queries.cql_queries import Neo4j
import time

api = Namespace('study', description="Add new study to database")
params = StudyNodeSchema.get_flask_model()
model = api.model('study', params['comments'])

parser = reqparse.RequestParser()
parser.add_argument(
    'X-Api-Token', location='headers', required=True,
    help='Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function.')


@api.route('/')
@api.doc(description="Add study-level data")
class StudyResource(Resource):
    study_schema = StudyNodeSchema()
    user_schema = UserNodeSchema()
    added_rel = AddedByRelSchema()

    @api.expect(model, validate=False)
    def post(self):
        logger_info()

        try:
            req = request.get_json()

            # load
            user = self.user_schema.load({"uid": get_user_email(request.headers.get('X-Api-Token'))})
            study = self.study_schema.load(req)
            try:
                rel = self.added_rel.load({'epoch': time.time(), "comments": req['comments']})
            except KeyError:
                rel = self.added_rel.load({'epoch': time.time()})

            # persist or update
            user.create_node()
            study.create_node()

            # link study to user; record epoch
            Neo4j.create_unique_rel("ADDED_BY", "Study", study['id'], "User", user['uid'], rel_props=rel,
                                    lhs_uid_key='id', rhs_uid_key='uid')

        except marshmallow.exceptions.ValidationError as e:
            raise BadRequest("Could not validate payload: {}".format(e))
