#!/usr/bin/env python

'''Python Image Organizer'''

import sys
import os
from os.path import join, getsize, basename, dirname
from optparse import OptionParser
import fnmatch
import EXIF

VALID_GLOB = ('.JPG', '.jpg')
IGNORE_GLOB = ('.*', '_*')
RENAME_FORMAT = "%(YYYY)s%(MM)s%(DD)s-%(HH)s%(MM)s%(SS)s"
ORGANIZED_DIR_FORMAT = "%(YYYY)s%(MM)s%(DD)s"

class CommandLineParameters(object):
    '''Parse Command Line Options'''

    def __init__(self):
        self.usage = "./pyImageOrg [options] <SOURCE_DIR>"
        self.parser = OptionParser(self.usage)
        self.options = None
        self.args = None
        self._add_options()
        self._validate_options()

    def _add_options(self):
        '''Add CL options'''
        
        self.parser.add_option('-v', '--verbose', action='store_true',
            dest='verbose')
        self.parser.add_option('-d', '--dry_run', action='store_true',
            dest='dry_run')
        self.parser.add_option('-r', '--recurse', action='store_true',
            dest='recurse')
        self.parser.add_option('-l', '--lower_case_ext', action='store_true',
            dest='lower_case_ext')
        self.parser.add_option('-u', '--upper_case_ext', action='store_true',
            dest='upper_case_ext')
        self.parser.add_option('-o', '--overwrite', action='store_true',
            dest='overwrite')
        self.parser.add_option('-z', '--organized_dir', action='store',
            dest='organized_dir', help='Dir to copy all renamed files into,'+\
            ' organized')
        (self.options, self.args) = self.parser.parse_args()

    def _validate_options(self):
        '''Validate the CL options'''
        
        if not self.options.recurse:
            print 'Recurse=False not implemented yet.'
            sys.exit(1)
        if len(self.args) != 1:
            print 'Invalid number of parameters', self.args
            sys.exit(1)
        if self.options.upper_case_ext and self.options.lower_case_ext:
            print 'Upper and Lower case are conflicting options.'
            sys.exit()


class OrganizeFiles(object):
    '''Organize Files'''

    def __init__(self, curr_file):
        pass


class ProcessFiles(object):
    '''Process image files'''
    
    def __init__(self, cmd_line):
        if cmd_line.options.verbose:
            print 'Processing Files'
        self.cmd_line = cmd_line
        self.new_name = None
        self.dto = {}
        self.target = None
        self.dto_str = None
        self.folder = None
        self._walk()

    def _walk(self):
        '''Walk the path'''
        
        for root, dirs, files in os.walk(self.cmd_line.args[0]):
            if self.cmd_line.options.verbose:
                print root, 'consumes',
                print sum(getsize(join(root, name)) \
                    for name in files) / (2 ** 20),
                print 'M in', len(files), 'non-directory files'
            for curr_file in files:
                skip = False
                for match in IGNORE_GLOB:
                    if fnmatch.fnmatch(curr_file, match):
                        skip = True
                if skip:
                    continue
                for match in VALID_GLOB:
                    if fnmatch.fnmatch(curr_file, match):
                        self._process_current(join(root, curr_file))

    def _get_extension(self, curr_file):
        '''Get/convert current file extention'''
        
        extension = '.' + curr_file.rsplit('.', 1)[1]
        if self.cmd_line.options.lower_case_ext:
            extension = extension.lower()
        return extension
        
    def _format_time(self, curr_file, tags):
        '''Format time'''
        
        self.dto_str = tags.get('EXIF DateTimeOriginal').values
        self.dto['date'], self.dto['time'] = self.dto_str.split(' ')
        self.dto['YYYY'], self.dto['MM'], self.dto['DD'] = \
            self.dto['date'].split(':')
        self.dto['HH'], self.dto['MM'], self.dto['SS'] = \
            self.dto['time'].split(':')
        self.new_name = RENAME_FORMAT % self.dto
        self.new_name = self.new_name + self._get_extension(curr_file)        

    def _process_current(self, curr_file):
        '''Process current file'''
        
        pfile = open(curr_file, 'rb')
        tags = EXIF.process_file(pfile)
        pfile.close()
        self._format_time(curr_file, tags)
        self.folder = dirname(curr_file)
        self.target = join(self.folder, self.new_name)
        print (curr_file, self.target)
        if not self.cmd_line.options.dry_run:
            try:
                os.rename(curr_file, self.target)
            except Exception, ex:
                print 'Rename Failed', ex
                sys.exit(1)


def main():
    '''Run everything'''
    
    cmd_line = CommandLineParameters()
    ProcessFiles(cmd_line)


if __name__ == "__main__":
    main()
