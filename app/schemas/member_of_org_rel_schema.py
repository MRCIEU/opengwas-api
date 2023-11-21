from marshmallow import fields

from schemas.frpm_schema import FRPMSchema


class MemberOfOrgRelSchema(FRPMSchema):
    job_title = fields.Float(required=False, description="Job title according to Microsoft Graph user resource.")
    department = fields.Float(required=False, description="Department according to Microsoft Graph user resource.")
