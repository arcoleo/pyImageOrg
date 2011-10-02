#!/usr/bin/env python

'''Rename all jpg files to XXXXX.jpg'''

import sys
import os
from optparse import OptionParser

options = args = None

def cmd_options():
    '''Parse Command Line Options'''
    global options, args

    usage = "./number [options] <SOURCE_DIR>"
    parser = OptionParser(usage)
    options = None
    args = None


    # Universal options
    parser.add_option('-v', '--verbose', action='store_true')
    parser.add_option('-d', '--dry_run', action='store_true')
    parser.add_option('-r', '--recurse', action='store_true')
    parser.add_option('-p', '--prefix', action='store')
    parser.add_option('-i', '--initial_offset', action='store', type='int')
    parser.add_option('-q', '--queue_errors', action='store_true', default=True, help='Queue errors instead of stopping on them')
                      
    (options, args) = parser.parse_args()

def process_files():
    prefix = ''
    if options.prefix:
        prefix = options.prefix
    initial_offset = 0
    if options.initial_offset:
        initial_offset = options.initial_offset
        
    for root, dirs, files in os.walk(args[0]):
        for index, curr_file in enumerate(files):
            #print index, prefix, curr_file
            basename, extension = os.path.splitext(curr_file)
            print basename, extension, '\t',
            tmp_target_name = 'tmp-%s-%05d%s' % (prefix, index+initial_offset, extension)
            target_name = '%s-%05d%s' % (prefix, index+initial_offset, extension)
            print target_name
            if not options.dry_run:
                try:
                    print '%s -> %s' % (curr_file, tmp_target_name)
                    os.rename(curr_file, tmp_target_name)
                except Exception, ex:
                    print curr_file, tmp_target_name
                    print 'Ex', ex
                    sys.exit()
        print 'Total of', len(files)
    for root, dirs, files in os.walk(args[0]):
        for index, curr_file in enumerate(files):
            basename, extension = os.path.splitext(curr_file)
            target_name = '%s-%05d%s' % (prefix, index+initial_offset, extension)
            if not options.dry_run:
                try:
                    print '%s -> %s' % (curr_file, target_name)
                    os.rename(curr_file, target_name)
                except Exception, ex:
                    print curr_file, target_name
                    print 'Ex', ex
                    sys.exit()
    
def main():
    cmd_options()
    process_files()

if __name__ == "__main__":
    main()
