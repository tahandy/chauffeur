#!/usr/bin/env python3
import random
import sys
import os

if __name__ == '__main__':
	# Load parameter file
	A = None
	S = None
	runid = None
	fileid = None
	with open('input.par','r') as f:
		lines = f.read().splitlines();
		A      = lines[0]
		S      = lines[1]
		runid  = lines[2]
		fileid = lines[3]


	# Write some random files to IO
	N = random.randint(2,10)
	for i in range(0,N):
		fname = os.path.join('IO','a{}_{}_{}_{:04d}.out'.format(A,S,runid,i))
		with open(fname,'w+') as f:
			sys.stdout.write('Writing {:s}\n'.format(fname))
			f.write('Heres some output\n')

