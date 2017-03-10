#!/usr/bin/env python3
import argparse
import sys

def is_prime(num):
	if(num<=2):
		return False
	if(num%2==0 and num>2):
		return False

	for x in range(3,int(num**0.5)+1,2):
		if(num%x==0):
			return False
	return True

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('num',type=int,default=0,help='number to check primarily of')
	args = parser.parse_args()
	num = args.num
	result = is_prime(num)
	if(result):
		sys.stdout.write('{:d} is prime\n'.format(num))
	else:
		sys.stdout.write('{:d} is not prime\n'.format(num))
