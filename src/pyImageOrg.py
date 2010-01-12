#!/usr/bin/env python

import sys
import os
from os.path import join, getsize, basename, dirname
from optparse import OptionParser
import EXIF

VALID_FILES = ('.JPG', '.jpg')
RENAME_FORMAT = "%(YYYY)s%(MM)s%(DD)s-%(HH)s%(MM)s%(SS)s"

class CommandLineParameters(object):

    def __init__(self):
        self.usage = "./pyImageOrg [options] <SOURCE_DIR>"
        self.parser = OptionParser(self.usage)
        self._add_options()
        self._validate_options()

    def _add_options(self):
        self.parser.add_option('-v', '--verbose', action='store_true', dest='verbose')
        self.parser.add_option('-d', '--dry_run', action='store_true', dest='dry_run')
        self.parser.add_option('-r', '--recurse', action='store_true', dest='recurse')
        self.parser.add_option('-l', '--lower_case_ext', action='store_true', dest='lower_case_ext')
        self.parser.add_option('-o', '--overwrite', action='store_true', dest='overwrite')
        (self.options, self.args) = self.parser.parse_args()

    def _validate_options(self):
        if len(self.args) != 1:
            print 'Invalid number of parameters', self.args


class ProcessFiles(object):

    def __init__(self, cl):
        if cl.options.verbose:
            print 'Processing Files'
        self.cl = cl
        self._walk()

    def _walk(self):
        for root, dirs, files in os.walk(self.cl.args[0]):
            if self.cl.options.verbose:
                print root, 'consumes',
                print sum(getsize(join(root, name)) for name in files) / (2 ** 20),
                print 'M in', len(files), 'non-directory files'
            for curr_file in files:
                if curr_file.endswith(VALID_FILES):
                    self._process_current(join(root, curr_file))


    def _get_extension(self, curr_file):
        extension = '.' + curr_file.rsplit('.', 1)[1]
        if self.cl.options.lower_case_ext:
            extension = extension.lower()
        return extension
        
    def _format_time(self, curr_file, tags):
        self.dto_str = tags.get('EXIF DateTimeOriginal').values
        self.dto = {}
        self.dto['date'], self.dto['time'] = self.dto_str.split(' ')
        self.dto['YYYY'], self.dto['MM'], self.dto['DD'] = self.dto['date'].split(':')
        self.dto['HH'], self.dto['MM'], self.dto['SS'] = self.dto['time'].split(':')
        self.new_name = RENAME_FORMAT % self.dto
        self.new_name = self.new_name + self._get_extension(curr_file)        

    def _process_current(self, curr_file):
        f = open(curr_file, 'rb')
        tags = EXIF.process_file(f)
        self._format_time(curr_file, tags)
        self.folder = dirname(curr_file)
        self.target = join(self.folder, self.new_name)
        print (curr_file, self.target)
        try:
            os.rename(curr_file, self.target)
        except Exception, ex:
            print 'Rename Failed', ex
            sys.exit(1)


def main():
    cl = CommandLineParameters()
    pf = ProcessFiles(cl)


if __name__ == "__main__":
    main()
