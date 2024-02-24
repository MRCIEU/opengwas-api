from marshmallow import fields
from schemas.frpm_schema import FRPMSchema


class OrgNodeSchema(FRPMSchema):
    uuid = fields.Str(required=True)
    ms_id = fields.Str(required=False, metadata={"description": "Microsoft Graph organization.id"})
    ms_name = fields.Str(required=False, metadata={"description": "Microsoft Graph organization.displayName "})
    ms_domains = fields.List(fields.Str, required=False, metadata={"description": "Microsoft Graph organization.verifiedDomains.name"})
    gh_name = fields.Str(required=False, metadata={"description": "University name from GitHub repo"})
    gh_domains = fields.List(fields.Str, required=False, metadata={"description": "University domain names from GitHub repo"})
