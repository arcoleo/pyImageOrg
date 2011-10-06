#!/usr/bin/env python

""" Consolidate images that are stored many folders deep into a single folder
"""

import sys
import os
from optparse import OptionParser
import random

EXTRA_FILES = ('.css', '.DS_Store', '.html', '.htm')

def parse_options():
    global options, args

    parser = OptionParser()
    parser.add_option('-v', '--verbose', action='store_true')
    parser.add_option('-u', '--unique_files', action='store_true',
                      help='Make new filenames unique to avoid collisions.',
                      default=True)
    parser.add_option('-l', '--levels', action='store', type='int',
                      default=1,
                      help='Number of level to condense by.')
    parser.add_option('-m', '--min_levels', action='store', type='int',
                      default=1,
                      help='Minimum number of levels of dirs to keep from root.')
    parser.add_option('-e', '--delete_empty_dirs', action='store_true',
                      default=True,
                      help='Delete empty folders')
    parser.add_option('--delete_extra_files', action='store_true', default=True)

    options, args = parser.parse_args()

    if not len(args):
        print 'Missing dir'
        sys.exit()


def walk(base_dir):
    print base_dir
    base_level = base_dir.count(os.path.sep)
    min_level = base_level + options.min_levels
    print 'min_level', min_level
    for dirname, dirnames, filenames in os.walk(base_dir, topdown=False):
        for subdirname in dirnames:
            curr_path = os.path.join(dirname, subdirname)
            try:
                file_lst = os.listdir(curr_path)
            except Exception, ex:
                pass
            print '\t', curr_path,
            if len(file_lst):
                print file_lst
            else:
                if options.delete_empty_dirs:
                    print 'Deleting Empty'
                    try:
                        os.removedirs(curr_path)
                    except Exception, ex:
                        pass
                else:
                    print
        for filename in filenames:
            curr_filename = filename
            curr_file = os.path.join(dirname, filename)
            print curr_file
            curr_level = curr_file.count(os.path.sep)
            print 'curr_level', curr_level - 1
            # loop for levels
            curr_dirname = dirname
            while (curr_level > min_level):

                parent_path, curr = os.path.split(curr_dirname)
                target_file = os.path.join(parent_path, curr_filename)
                try:
                    print 'Moving', curr_file, 'to ', target_file
                    if not os.path.exists(target_file):
                        os.rename(curr_file, target_file)
                    else:
                        print 'Target file exists.  Renaming'
                        r = random.randint(1, 10000)-1
                        target_file = os.path.join(parent_path, '%05d-%s' % (r, curr_filename))
                        print 'New file:', target_file
                        if not os.path.exists(target_file):
                            os.rename(curr_file, target_file)
                        else:
                            print 'Target file exist', target_file
                            print 'Not overwriting.'
                            sys.exit()
                except Exception, ex:
                    print 'Ex 3', ex
                    print 'Failed to move to', target_file
                    sys.exit()
                curr_file = target_file
                curr_dirname = parent_path
                curr_level = curr_file.count(os.path.sep)

            if options.delete_extra_files and filename.endswith(EXTRA_FILES):
                try:
                    os.remove(curr_file)
                except Exception, ex:
                    pass





if __name__ == '__main__':
    parse_options()
    walk(args[0])

