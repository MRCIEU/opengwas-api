

def get_mrbase_access_token():
	import subprocess, os
	#subprocess.call("Rscript -e \"write.table(TwoSampleMR::get_mrbase_access_token(), file='token.temp', row=F, col=F, qu=F)\"", shell=True)
	with open('token.temp', 'r') as tokenfile:
		token = tokenfile.read().replace('\n','')
	#os.remove('token.temp')
	return token

