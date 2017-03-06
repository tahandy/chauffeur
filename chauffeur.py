#!/usr/bin/env python3

## Copyright 2017 Timothy A. Handy
##
## Permission is hereby granted, free of charge, to any person obtaining
## a copy of this software and associated documentation files (the "Software"),
## to deal in the Software without restriction, including without limitation
## the rights to use, copy, modify, merge, publish, distribute, sublicense,
## and/or sell copies of the Software, and to permit persons to whom the
## Software is furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included
## in all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
## OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.

import sys
from pathlib import Path
import os
import time
import queue
import threading
import shutil
import subprocess
import yaml
import pyaml
import itertools as it
from collections import OrderedDict
import logging
import argparse

from math import sqrt, pow

# Global configuration options
driverData = dict()
userData   = dict()
runData    = OrderedDict()
fileData   = OrderedDict()
fmtShort   = dict()
fmtLong    = dict()

pbsRundirs = []
pbsFiles   = []

wetRun = True

# Create logger and setup to go to stdout. This allows us
# to redirect the log output via > in the command line
logger = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('[%(asctime)s t-%(threadName)s] %(levelname)s: %(message)s',
	                                    datefmt='%m/%d/%Y %H:%M:%S'))
out_hdlr.setLevel(logging.INFO)
logger.addHandler(out_hdlr)
logger.setLevel(logging.INFO)

#============================================
# abort: Helper function to abort execution
#============================================
def abort(msg):
	"""Abort execution and print critical log message"""
	callerName = sys._getframe(1).f_code.co_name
	output = '['+callerName+'] '+msg
	logger.critical(output)
	sys.exit(1)

def logInfo(msg):
	"""Wrapper for the information-level logger"""
	logger.info(msg)

#===============================================
# resolveAbsPath: Convert paths to absolute
#===============================================
def resolveAbsPath(pathIn):
	"""Given a path, resolve it to an absolute path"""

	if(pathIn is None):
		return None
	pathOut = pathIn
	pathOut = pathOut.replace('~',os.path.expanduser('~'))
	baseDir = ''
	if(not os.path.isabs(pathOut)):
		baseDir = os.getcwd();
	pathOut = os.path.join(baseDir,pathOut)
	pathOut = os.path.normpath(pathOut)
	return pathOut

#============================================
# printCfg: Helper function to print configuration
#============================================
def printCfg():
	"""Pretty print current state's YAML configuration"""

	cfg = dict()
	cfg['driver']  = driverData
	cfg['userdef'] = userData
	for key in runData:
		cfg[key] = runData[key]
	yaml.safe_dump(cfg,sys.stdout, default_flow_style=False)

#============================================
# getThreadInfo: Helper function to get thread information
#============================================
def getThreadInfo():
	"""Get information about the current thread in a dict"""

	info = dict()
	info['thread'] = threading.current_thread().getName()
	return info

#============================================
# initDriverData: Initialize driver control
# data with defaults and then overwrite with
# config-defined values
#============================================
def initDriverData(cfg):
	"""Initialize and extract driver parameters from the YAML configuration"""

	# Defaults
	driverData['cwd']           = os.getcwd()
	driverData['scriptdir']     = os.path.realpath(__file__)
	driverData['executable']    = None
	driverData['rundir']        = None
	driverData['templatefile']  = None
	driverData['paramfile']     = None
	driverData['templatedir']   = None
	driverData['type']          = 'exec'
	driverData['dryrun']        = True
	driverData['nthreads']       = 1

	driverData['precommand']    = None
	driverData['execcommand']   = None
	driverData['postcommand']   = None

	# PBS stuff
	driverData['pbs_submitscript'] = '%(cwd)/pbs_submit.sh'
	driverData['pbs_subcommand']   = 'qsub'

	# Type formats
	driverData['intFmtLong']   = 'd'
	driverData['fltFmtLong']   = '12.7e'
	driverData['intFmtShort']  = '05d'
	driverData['fltFmtShort']  = 'f'

	# Load user-defined values
	cfgKey = 'driver'
	if(cfgKey in cfg):
		for key in cfg[cfgKey]:
			if(key.lower() not in driverData):
				abort('Key "'+key+'" not accepted. Options are: '+', '.join(driverData.keys()))
			driverData[key.lower()] = cfg[cfgKey][key]

	# Setup type -> format mappings
	fmtLong[type(1)]    = driverData['intFmtLong']
	fmtLong[type(1.0)]  = driverData['fltFmtLong']
	fmtShort[type(1)]   = driverData['intFmtShort']
	fmtShort[type(1.0)] = driverData['fltFmtShort']

	# Setup non-dict globals
	wetRun = not driverData['dryrun']

#============================================
# initUserData: Initialize custom user-defined
# data
#============================================
def initUserData(cfg):
	"""Extract user defined parameters from the YAML configuration"""

	# Load user-defined values
	cfgKey = 'userdef'
	if(cfgKey in cfg):
		for key in cfg[cfgKey]:
			userData[key.lower()] = cfg[cfgKey][key]


#============================================
# initRunData: Initialize relevant run data
# This performs the following:
#	1) Searches for all top-level keys containing 'run'
#	2) Sorts them lexicographically
#============================================
def initRunData(cfg):
	"""Extract 'run' parameters from the YAML configuration"""

	# Extract all top-level keys containing 'run'
	keyList = [key for key in cfg if 'run' in key.lower()]
	if(not keyList):
		abort('No run sections declared!')

	# Sort the list
	keyList = sorted(keyList)

	restrNames = ['variableorder']

	# Read in the individual run data
	for key in keyList:
		rdata = cfg[key]
		varSet   = {v for v in rdata['variables']}

		# Construct the variableorder field if necessary
		if('variableorder' not in rdata):
			rdata['variableorder'] = list(varSet)
		else:
			# Confirm that all expected variable data is in the 'variableorder' field
			if(not varSet == set(rdata['variableorder'])):
				abort('Provided variable order and parsed variables are not the same')

		# Ensure that all variable values are lists
		# If they're not (e.g. a single int is the variable value),
		# convert them to a single-element list
		for v in rdata['variables']:
			if(type(rdata['variables'][v]) is not list):
				rdata['variables'][v] = [rdata['variables'][v]]

		# Store run data
		runData[key.lower()] = rdata


#============================================
# initFileData: Initialize relevant data about
# files that need to be processed.
#============================================
def initFileData(cfg):
	"""Extract 'file' parameters from the YAML configuration"""

	# Extract all top-level keys containing 'run'
	keyList = [key for key in cfg if 'file' in key.lower()]
	if(not keyList):
		abort('No file sections declared!')

	# Sort the list
	keyList = sorted(keyList)

	# Read in the individual file data
	for key in keyList:

		# Set defaults
		rdata = dict()
		rdata['input']  = None
		rdata['output'] = None
		rdata['type']   = None
		rdata['parameters']   = None

		cdata = cfg[key]

		for k in cdata.keys():
			if(k.lower() not in rdata.keys()):
				abort('File key "'+k+'" not accepted. Options are: '+', '.join(rdata.keys()))
			rdata[k.lower()] = cdata[k]

		# Store file data
		fileData[key.lower()] = rdata

#============================================
# generateProduct: Compute the cartesian product of
# all variables in a given order. This assumes that
# order is structured as [fastest --> slowest]
# changing variable. The use of reversed(...)
# is then required due to the order in which
# itertools.product generates the cartesian product.
#============================================
def generateProduct(dicts,order):
	"""Generate the Cartesian product of a dictionary of parameters"""

	lists = []
	for v in reversed(order):
		lists.append(dicts[v])
	return list(dict(zip(reversed(order), x)) for x in it.product(*lists))


#============================================
# interpolateString: Recursively replace
# parameters in a given string based on
# driver, user, and [optional] input data
#============================================
def interpolateString(inStr, inputData=None, inputFmt=None, nCalls=0):
	"""Given an input string, replace all parameters and return the resolved string"""

	# logInfo('[interpolateString] inStr: %s    nCalls: %d    type:%s'%(inStr,nCalls,type(inStr)))

	MAX_RECURS = 10
	begStr = '%('
	endStr = ')'

	if(inStr is None):
		return None

	if(not isinstance(inStr,str)):
		return inStr

	outStr = inStr

	if(nCalls>=MAX_RECURS):
		abort('Maximum number of recursions exceeded ({})'.format(MAX_RECURS))

	# Get thread information
	threadInfo = getThreadInfo()

	# Move through the input string, replacing all found
	# parameters in turn
	countBeg = 0
	indBeg   = -1
	indEnd   = -1
	while(True):
		# Attempt to find the first instance of the
		# parameter identifier. If found, attempt to
		# find the parameter end. If the beginning
		# identifier is found, there are no more parameters
		# in the string and we can abort.
		indBeg = inStr.find(begStr, countBeg)
		if(indBeg>=0):
			indEnd = inStr.find(endStr, indBeg+1)
		else:
			break

		if(indBeg>0 and indEnd<0):
			abort('Potentially malformed string "%s"'%inStr)

		# Once a parameter has been identified, we will
		# begin attempting to resolve it. Resolution occurs
		# using defined values in the following order:
		# 1) driver values
		# 2) user values
		# 3) input values [optional]
		# Input values are passed as a dictionary to this function,
		# and are meant to be used to resolve strings that depend
		# on a particular choice of variable data (specific tuple of data).
		#
		# If an input value is used, we also check to see if the type of
		# the resolved value is provided a format. If so, we use that to
		# generate the resolved string. Otherwise, we use default formatting.
		subStr = inStr[indBeg+len(begStr):indEnd]

		inlineFmt = None
		indTmp = subStr.find(':')
		if(indTmp>=0):
			inlineFmt = subStr[indTmp+1:]
			subStr    = subStr[:indTmp]

		resolvedValue = None
		usedInput = False
		tmpFmt = None
		if(threadInfo is not None):
			if(subStr in threadInfo.keys()):
				resolvedValue = threadInfo[subStr]
		if(inputData is not None):
			if(subStr in inputData.keys()):
				resolvedValue = inputData[subStr]
		if(subStr in userData.keys()):
			resolvedValue = userData[subStr]
		if(subStr in driverData.keys()):
			resolvedValue = driverData[subStr]
		if(resolvedValue is None):
			abort('Unable to fully resolve "{}"'.format(begStr+subStr+endStr))

		# Recurse if the resolution results in another parameter
		resolvedValue = interpolateString(resolvedValue, inputData, inputFmt, nCalls+1)

		# If the result is an evaluatable expression (encased by ` characters),
		# perform the evaluation call. Evaluate string is, itself, recursive.
		resolvedValue = evaluateStr(resolvedValue)


		if(inlineFmt is not None):
			resolvedValue = ('{:'+inlineFmt+'}').format(resolvedValue)
		elif(inputFmt is not None and type(resolvedValue) in inputFmt.keys()):
			resolvedValue = ('{:'+inputFmt[type(resolvedValue)]+'}').format(resolvedValue)
		else:
			resolvedValue = '{}'.format(resolvedValue)


		# Update the string with the resolved value and prepare to find next
		# parameter
		outStr = outStr.replace(inStr[indBeg:indEnd+1],resolvedValue)

		countBeg = indEnd+1

	# Final return!
	return outStr

#============================================
# evaluateStr: Recursively evaluate embedded
# expressions in the provided string
#============================================
def evaluateStr(inStr):
	if(not isinstance(inStr,str)):
		return inStr

	inds = [i for i, char in enumerate(inStr) if char == '`']
	N = len(inds)

	if(N==0):
		return inStr

	if(N%2 != 0):
		abort('Odd number of evaluator characters (`) found in {:s}'.format(inStr))

	outStr = inStr
	N=N/2
	if(N==1):
		outStr = eval(inStr[1:-1])
	else:
		subStr   = inStr[inds[0]+1:inds[-1]-1]
		evaldStr = evaluateStr(subStr)
		# outStr   = outStr.replace(subStr,evaldStr)
		outStr   = evaldStr

	return outStr

#============================================
# processFiles: Process all defined files.
# Helper wrapper for processSingleFile
#============================================
def processFiles(instanceData):
	if(not fileData):
		return

	for fileKey in fileData.keys():
		processSingleFile(fileKey,instanceData)


#============================================
# processSingleFile: Process a single file
# with global and instance parameters
#============================================
def processSingleFile(fileKey,instanceData):
	if(fileKey not in fileData.keys()):
		abort('Attempting to process nonexistent file with key '+fileKey)

	# Merge instance data (from specific run instance) and the file's parameters
	data = instanceData
	if('parameters' in fileData[fileKey].keys()):
		data = {**data,**fileData[fileKey]['parameters']}


	# Load parameter template
	templatefile = resolveAbsPath(interpolateString(fileData[fileKey]['input'],data))
	logInfo('Loading template file {}'.format(templatefile))
	if(templatefile is None):
		abort('Parameter template file is None!')

	with open(templatefile,'r') as pfile:
		paramStr = pfile.read()

	# Replace all parameterizations with driver, user, and instance data
	paramStr = interpolateString(paramStr, data, fmtLong)

	# Write parameter file
	outputFile = resolveAbsPath(interpolateString(fileData[fileKey]['output'],data))
	logInfo('Writing param file {}'.format(outputFile))
	with open(outputFile,'w+') as pfile:
		pfile.write(paramStr)

	# If the file is of type "pbs", record its output name
	if(fileData[fileKey]['type'] == 'pbs'):
		logInfo('adding to pbs files: {:s}'.format(outputFile))
		pbsFiles.append(outputFile)

def constructPbsSubmitScript():
	if(not pbsFiles):
		return

	header = "#!/bin/bash"
	subscript = interpolateString(driverData['pbs_submitscript'])
	logInfo('Creating PBS submission script: {:s}'.format(subscript))
	with open(subscript,'w+') as output:
		output.write(header)
		output.write('\n')
		for f in pbsFiles:
			path, file = os.path.split(f)
			output.write('cd {:s} && {:s} {:s} && cd -\n'.format(path,driverData['pbs_subcommand'],file))


#============================================
# worker: Function called for each thread.
# Pulls a set of data off the run queue
# (from the cartesian product) and executes
# relevant activities
#============================================
def worker():
	"""Execute the driver specifications for a given set of parameters (threaded)"""

	while True:
		data = runqueue.get()
		if data is None:
			return

		# Copy template to working directory
		workDir = resolveAbsPath(interpolateString(driverData['rundir'],data))

		# If the workDir exists, skip this run
		#if(os.path.exists(workDir)):
		#	logInfo('Work directory {:s} exists. Skipping this run.'.format(workDir))
		#	continue



		templateDir = driverData['templatedir']
		if(templateDir is not None):
			logInfo('Copying %s to %s'%(templateDir,workDir))
			if(wetRun):
				shutil.copytree(templateDir,workDir,symlinks=True)

		if(wetRun):

			# Ensure that run directory exists. If not, create it.
			if(not os.path.exists(workDir)):
				logInfo('Creating run directory %s'%workDir)
				path = Path(workDir)
				path.mkdir(parents=True)

			# Process files
			processFiles(data)

			if(driverData['type'] in ['param_only','setup']):
				continue

			# Perform postprocessing commands
			if(driverData['precommand'] is not None):
				precommand = interpolateString(driverData['precommand'],data)
				cmdStr = 'cd %s; %s'%(workDir,interpolateString(precommand))
				logInfo('Executing pre command: {}'.format(precommand))
				proc = subprocess.Popen(cmdStr, shell=True)
				proc.wait()

			# Run executable in working directory
			if(driverData['executable'] is None):
				abort('No executable set in input file')

			if(driverData['execcommand'] is not None):
				execcommand = interpolateString(driverData['execcommand'],data)
				cmdStr = 'cd %s; %s'%(workDir,interpolateString(execcommand))
				logInfo('Executing exec command: {}'.format(execcommand))
				proc = subprocess.Popen(cmdStr, shell=True)
				proc.wait()

			# Perform postprocessing commands
			if(driverData['postcommand'] is not None):
				postcommand = interpolateString(driverData['postcommand'],data)
				cmdStr = 'cd %s; %s'%(workDir,postcommand)
				logInfo('Executing post command: {}'.format(postcommand))
				proc = subprocess.Popen(cmdStr, shell=True)
				proc.wait()


#============================================
# setupParser: Setup command line argument parser
#============================================
def setupParser():
	"""Setup the argument parser and return the parser object"""

	parser = argparse.ArgumentParser()
	parser.add_argument('-i','--input',default='input.yaml',help='specify input YAML file')
	return parser

#============================================
#                   MAIN
#============================================
if(__name__ == "__main__"):

	# Parser arguments and read YAML configuration file
	parser = setupParser();
	args = parser.parse_args()

	with open(args.input,'r') as f:
		cfg = yaml.safe_load(f)

		# Initialize driver configuration
		initDriverData(cfg)
		# Initialize user configuration
		initUserData(cfg)
		# Initialize file configurations
		initFileData(cfg)
		# Initialize run configurations
		initRunData(cfg)

	# Construct cartesian product of variables for each run
	runs = []
	for r in runData.keys():
		tmp = generateProduct(runData[r]['variables'],runData[r]['variableorder'])

		# Append run parameters to each of the generated subruns
		if('parameters' in runData[r].keys()):
			for i in range(0,len(tmp)):
				tmp[i].update(runData[r]['parameters'])

		runs.extend(tmp)
		# runs.extend(generateProduct(runData[r]['variables'],runData[r]['variableorder']))

	runqueue = queue.Queue()
	for r in runs:
		logInfo('Adding run info {}'.format(r))
		runqueue.put(r)

	threads = [ threading.Thread(target=worker, name='{:02d}'.format(_i)) for _i in range(driverData['nthreads']) ]
	for thread in threads:
		thread.daemon = True
		logInfo('Starting thread')
		thread.start()
		runqueue.put(None)  # one EOF marker for each thread


	# Keep master thread alive and check to see if all threads are done
	while True:
		time.sleep(1)
		allAlive = True
		for thread in threads:
			if not thread.isAlive():
				allAlive = False

		if(not allAlive):
			break

	# Construct PBS submission script
	constructPbsSubmitScript()
