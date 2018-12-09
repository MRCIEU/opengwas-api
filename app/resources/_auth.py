import urllib
import json
# from logger import *

OAUTH2_URL = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token='
# USERINFO_URL = 'https://www.googleapis.com/oauth2/v1/userinfo?alt=json&access_token='


def get_user_email(token):
	url = OAUTH2_URL + str(token)
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	if "email" in data:
		return data['email']
	else:
		return token

def check_access_token(token):
	url = OAUTH2_URL + token
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	if "email" in data:
		if check_email(data['email']):
			return "internal"
		else:
			return "conditional"
	else:
		return "public"

def token_query(token):
	user_email = get_user_email(token)
	# logger2.debug("getting credentials for "+user_email)
	query =  """(c.id IN (select d.id from study_e d, memberships m, permissions_e p
					WHERE m.uid = "{0}"
					AND p.gid = m.gid
					AND d.id = p.study_id
				)
				OR c.id IN (select d.id from study_e d, permissions_e p
					WHERE p.gid = 1
					AND d.id = p.study_id
				))""".format(user_email)
	#logger2.debug(query)
	return query
