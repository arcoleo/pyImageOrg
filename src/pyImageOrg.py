#!/usr/bin/env python

'''Python Image Organizer'''

import sys
import os
from os.path import join, getsize, basename, dirname
from optparse import OptionParser
import fnmatch
import shutil
import EXIF
import filecmp
import logging

VALID_GLOB = ('*.JPG', '*.jpg')
IGNORE_GLOB = ('.*', '_*')
RENAME_FORMAT = "%(YYYY)s%(MM)s%(DD)s-%(HH)s%(mm)s%(SS)s"
ORGANIZED_DIR_FORMAT = "%(YYYY)s/%(MM)s/%(DD)s"

 
def init_logging(level='debug', log_file='', log_dir='.'):
    '''Initialize logging'''

    global log, console

    #if not os.path.exists(log_dir):
    #    os.mkdir(log_dir)
    LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

    log_str = '[%(asctime)s] [%(levelname)s] [%(filename)s] [%(funcName)s:%(lineno)d] %(message)s'
    log_str_lite = '[%(levelname)s] [%(funcName)s:%(lineno)d] %(message)s'

    try:
        logging.basicConfig(level=LOGGING_LEVELS[level], #logging.DEBUG,
            format=log_str_lite,
            datefmt='%a %b %d %H:%M:%S %Y',
            #filename=os.path.join(log_dir, log_file),
            filemode='a')
    except Exception, ex:
        print 'Log Error', ex

    log = logging.getLogger('log')


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
        self.parser.add_option('-c', '--confirm_every', action='store_true',
            dest='confirm_every', help='Confirm every action')
        self.parser.add_option('--confirm_once', action='store_true',
            dest='confirm_once', help='Confirm all renames once')
        self.parser.add_option('-z', '--organized_dir', action='store',
            dest='organized_dir', help='Dir to copy all renamed files into,'+\
            ' organized', default='')
        self.parser.add_option('-e', '--organize_existing', action='store_true',
            dest='organize_existing', help='Organize existing files in ' +\
            'ORGANIZED_DIR according to existing rules')
        self.parser.add_option('-q', '--queue_errors', action='store_true',
            dest='queue_errors', help='Queue errors instead of stopping on them')
        self.parser.add_option('-p', '--delete_dupes', action='store_true',
            dest='delete_dupes', help='delete duplicates (source)')
        (self.options, self.args) = self.parser.parse_args()

    def _validate_options(self):
        '''Validate the CL options'''
        
        if not self.options.recurse:
            log.error('Recurse=False not implemented yet.')
            sys.exit(1)
        if len(self.args) != 1:
            log.error(('Invalid number of parameters:', self.args))
            sys.exit(1)
        if self.options.upper_case_ext and self.options.lower_case_ext:
            log.error('Upper and Lower case are conflicting options.')
            sys.exit(1)
        if (self.options.organized_dir == None) and self.options.organize_existing:
            log.error('--organize_existing requires --organized_dir')
            sys.exit(1)
        if self.options.confirm_every and self.options.confirm_once:
            log.error('Cannot have both --confirm_every and --confirm_once')
            sys.exit(1)

        level = 'warning'
        if self.options.verbose:
            level = 'debug'
        init_logging(level=level)


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
                consume = sum(getsize(join(root, name)) \
                    for name in files) / (2 ** 20),
                log.info(root + 'consumes' + str(consume) + 'M in' +
                    str(len(files)) + 'non-directory files')
            for curr_file in files:
                if self.cmd_line.options.verbose:
                    log.debug(('curr_file', curr_file))
                skip = False
                for match in IGNORE_GLOB:
                    if fnmatch.fnmatch(curr_file, match):
                        skip = True
                if skip:
                    log.debug('skipping')
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

    def _extract_tags(self, tags):
        return tags
        
    def _format_filename(self, curr_file, tags):
        '''Format time'''

        try:
            self.dto_str = tags.get('EXIF DateTimeOriginal').values
        except AttributeError, ex:
            log.error(('Attribute error', ex, curr_file))
            if not self.cmd_line.options.queue_errors:
                sys.exit(1)
            else:
                raise Exception("Skip")
                sys.exit()
        except Exception, ex:
            print 'Error', ex, curr_file
            if not self.cmd_line.options.queue_errors:
                sys.exit(1)
            else:
                raise
            
        self.dto['date'], self.dto['time'] = self.dto_str.split(' ')
        self.dto['YYYY'], self.dto['MM'], self.dto['DD'] = \
            self.dto['date'].split(':')
        self.dto['HH'], self.dto['mm'], self.dto['SS'] = \
            self.dto['time'].split(':')
        self.new_name = RENAME_FORMAT % self.dto
        self.new_name = self.new_name + self._get_extension(curr_file)

    def _queue_quit(self):
        if not self.cmd_line.options.queue_errors:
            sys.exit(1)

    def _format_dirname(self, curr_dir, tags):
        self.organized_dir = join(self.cmd_line.options.organized_dir,
            ORGANIZED_DIR_FORMAT % self.dto)
        log.debug(('organized_dir', self.organized_dir))

    def _process_current(self, curr_file):
        '''Process current file'''

        try:
            pfile = open(curr_file, 'rb')
            self.tags = self._extract_tags(EXIF.process_file(pfile))
            pfile.close()
            self._format_filename(curr_file, self.tags)
            self._format_dirname(dirname(curr_file), self.tags)
            self.folder = dirname(curr_file)
            self.target = join(self.folder, self.new_name)
            log.debug(('process_current', curr_file, self.target))
            if not self.cmd_line.options.dry_run:
                try:
                    os.rename(curr_file, self.target)
                except Exception, ex:
                    log.error(('Rename Failed', ex))
                    if not self.cmd_line.options.queue_errors:
                        sys.exit(1)
                    else:
                        raise
            self._move_current()
        except Exception, ex:
            log.error(('Skipped rename', self.target, ex))


    def _move_current(self):
        '''Move file'''
        log.debug(('curr_file_move', self.target, join(self.organized_dir, self.new_name)))

        log.debug('Creating target dir')
        if not self.cmd_line.options.dry_run:
            try:
                os.makedirs(self.organized_dir)
            except Exception, (errno, ex):
                if errno in [17]:
                    pass
                else:
                    log.critical(('makedirs failed', errno, ex))
                    sys.exit(2)

        log.debug('Moving file')
        if not self.cmd_line.options.dry_run:
            try:
                shutil.move(self.target, self.organized_dir)
            except shutil.Error, ex:
                if 'already exists' in str(ex):
                    if self.cmd_line.options.overwrite:
                        if filecmp.cmp(self.target, join(self.organized_dir, self.new_name)):
                            if self.cmd_line.options.delete_dupes:
                                try:
                                    os.remove(self.target)
                                except Exception, ex:
                                    log.critical((self.target, ex))
                                    sys.exit()
                        else:
                            log.error((self.target, 'and',
                                join(self.organized_dir, self.new_name), 'differ'))
                            self._queue_quit()
                    else:
                        log.critical((sys.exc_info()))
                        sys.exit(3)
            except Exception, ex:
                log.error(('move failed', ex))
                self._queue_quit()


def main():
    '''Run everything'''

    cmd_line = CommandLineParameters()
    ProcessFiles(cmd_line)


if __name__ == "__main__":
    main()
