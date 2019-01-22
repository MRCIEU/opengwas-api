from flask_restplus import Resource, reqparse, abort, Namespace
from resources._ld import *
from schemas.study_node_schema import StudyNodeSchema

api = Namespace('study', description="Add new study to database")

parser = reqparse.RequestParser()
parser.add_argument('id', required=True, type=str, action='append', help="Identifier for new study")
parser.add_argument('pmid', required=True, type=int, action='append', help="Identifier for PubMed publication")
parser.add_argument('year', required=True, type=int, action='append', help="Year of publication")
parser.add_argument('filename', required=True, type=str, action='append', help="Name of file")
parser.add_argument('path', required=True, type=str, action='append', help="Path to file")
parser.add_argument('mr', required=True, type=int, action='append', help="Is suitable for MR analysis?")
parser.add_argument('note', required=False, type=str, action='append', help="Comments section")
parser.add_argument('trait', required=True, type=str, action='append', help="Comments section")


for func in dir(StudyNodeSchema):
    print(func)


@api.route('/')
@api.doc(description="Add a new study to the database")
class Study(Resource):
    schema = StudyNodeSchema()

    @api.expect()
    def post(self):
        logger_info()
        args = self.schema.load(parser.parse_args())
        # user_email = get_user_email(request.headers.get('X-Api-Token'))
        print(args)
