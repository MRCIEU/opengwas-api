import pandas as pd
import gzip
import re
import numpy as np
import matplotlib.pyplot as plt
plt.style.use('seaborn-deep')

def read_logs(fileName,plotName):
	print('Reading '+fileName)
	esList = []
	clumpList = []
	proxyList = []
	with gzip.open(fileName) as f:
		for line in f:
			#es
			m = re.match(r'.*Time taken: (.*?) seconds',line)
			if m:
				esList.append(float(m.group(1)))
			m = re.match(r'.*clumping: took (.*?) seconds',line)
			if m:
				#print line
				clumpList.append(float(m.group(1)))
			m = re.match(r'.*proxy matching took :(.*?) seconds',line)
			if m:
				#print line
				proxyList.append(float(m.group(1)))
	#print proxyList
	print('Making plot...')
	bins = np.linspace(0, 50, 50)
	#x = np.random.normal(1, 2, 5000)
	#y = np.random.normal(-1, 3, 2000)
	#print x
	es = np.asarray(esList)
	cl = np.asarray(clumpList)
	pr = np.asarray(proxyList)
	#print y
	#print bins
	plt.hist([es,cl,pr], bins, label=['ES', 'Clumping', 'Proxies'])
	plt.legend(loc='upper right')
	plt.yscale('log', nonposy='clip')
	#plt.show()
	plt.savefig(plotName)

testFile='../times/test.log.gz'
fullFile='../times/mrbaseapi.log.gz'
read_logs(fullFile,'../times/march_27_2018.pdf')
