from flask_restplus import Resource, Namespace
from schemas.study_node_schema import StudyNodeSchema
from queries.study_node import Study as StudyNode

api = Namespace('Study', description="Add new study to database")
model = api.model('Study', StudyNodeSchema.get_flask_model())
schema = StudyNodeSchema()


@api.route('/')
@api.doc(description="Access and add study-level data")
class StudyResource(Resource):
    def get(self):
        return StudyNode.get_node('2')

    @api.expect(model, validate=False)
    def post(self):
        pass
