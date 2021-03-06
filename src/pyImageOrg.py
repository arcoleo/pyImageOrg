#!/usr/bin/env python

'''Python Image Organizer'''

import sys
import os
from os.path import join, getsize, basename, dirname, exists
#from optparse import OptionParser
import argparse
import fnmatch
import shutil
from errno import EEXIST
import logging
import ConfigParser
import filecmp
import EXIF
import Image
from pprint import pprint

foobar = None

VALID_GLOB = ('*.JPG', '*.jpg', '*.nef', '*.NEF', '*.dng', '*.DNG')
IGNORE_GLOB = ('.*', '_*')
RENAME_FORMAT = "%(YYYY)s%(MM)s%(DD)s-%(HH)s%(mm)s%(SS)s%(MakerNoteTotalShutterReleases)s"
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
        logging.basicConfig(level=LOGGING_LEVELS[level],  # logging.DEBUG,
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
        self.parser = argparse.ArgumentParser(description='Process some images.')
        self.options = None
        self.args = None
        self.skip_processfiles = False
        self._add_options()
        self._validate_options()

    def _add_options(self):
        '''Add CL options'''

        # read rc file
        self.parser.add_argument('--rc', action='store',
           dest='rcfile', help='Location of rc file to read options from')

        # Universal options
        self.parser.add_argument('-v', '--verbose', action='store_true', dest='verbose')
        self.parser.add_argument('-d', '--dry-run', action='store_true')

        recurse_group = self.parser.add_mutually_exclusive_group()
        recurse_group.add_argument('-r', '--recurse', action='store_true', default=True)
        recurse_group.add_argument('--no-recurse', action='store_true', default=False)
        
        self.parser.add_argument('-o', '--overwrite', action='store_true')
        self.parser.add_argument('-q', '--queue-errors', action='store_true',
            default=True, help='Queue errors instead of stopping on them')

        # Organizing options
        case_group = self.parser.add_mutually_exclusive_group()
        case_group.add_argument('-l', '--lower-case-ext', action='store_true', default=True)
        case_group.add_argument('-u', '--upper-case-ext', action='store_true')
        
        self.parser.add_argument('-z', '--organized-dir', action='store',
            help='Dir to copy all renamed files into, organized', default='')
        self.parser.add_argument('-e', '--organize-existing',
            action='store_true',
            help='Organize existing files in ORGANIZED_DIR according to existing rules')

        # Mirroring options
        self.parser.add_argument('--compressed-mirror', action='store',
            help='Dir to maintain as a mirror of organized_dir, but smaller.')
        self.parser.add_argument('--compressed-dimension', action='store',
            type=int, default=1600,
            help='Square dimension of compression.  800 for example compresses to 800x800')

        # EXIF tags
        self.parser.add_argument('--exif-dimension', action='store', type=int,
            help='Store long side of image dimension in EXIF')
        # Unknown options
        self.parser.add_argument('-c', '--confirm-every', action='store_true', help='Confirm every action')
        self.parser.add_argument('--confirm-once', action='store_true', help='Confirm all renames once')
        self.parser.add_argument('-p', '--delete-dupes', action='store_true', help='delete duplicates (source)')
        
        self.parser.add_argument('source_folder', nargs='?')
        self.args = vars(self.parser.parse_args())


    def _validate_options(self):
        '''Validate the CL options'''

        # Validate required parameters
        if self.args.get('source_folder') is None:
            # some options don't need the base parameter
            if self.args.get('compressed_mirror'):
                self.skip_processfiles = True
                print 'Skipping Processed Files'
            else:
                print 'Not Skipping Processed Files'
            if not self.skip_processfiles:
                print(('Invalid number of parameters:', self.args))
                sys.exit(1)

        # Validate universal options
        if (not self.args.get('recurse')) or self.args.get('no_recurse'):
            print('Recurse=False not implemented yet.')
            pprint(self.args)
            sys.exit(1)

        # Validate organizing options
        if self.args.get('upper_case_ext') and self.args.get('lower_case_ext'):
            print('Upper and Lower case are conflicting options.')
            sys.exit(1)

        if (self.args.get('organized_dir') is None) and \
            self.args.get('organize_existing'):
            print('--organize_existing requires --organized_dir')
            sys.exit(1)

        # Validate mirroring options
        if self.args.get('compressed_dimension') and \
            (self.args.get('compressed_dimension') < 1):
            print('Invalid compressed dimension')
            sys.exit(1)

        # Validate unknown options
        if self.args.get('confirm_every') and self.args.get('confirm_once'):
            print('--confirm_every and --confirm_once conflict')
            sys.exit(1)

        level = 'warning'
        if self.args.get('verbose'):
            level = 'debug'
        init_logging(level=level)


class OrganizeFiles(object):
    '''Organize Files'''

    def __init__(self, curr_file):
        pass


class ProcessFiles(object):
    '''Process image files'''

    def __init__(self, cmd_line):
        log.debug('Processing Files')
        self.cmd_line = cmd_line
        self.new_name = None
        self.dto = {}
        self.target = None
        self.dto_str = None
        self.folder = None
        self._walk()

    def _walk(self):
        '''Walk the path'''

        for root, dirs, files in os.walk(self.cmd_line.args.get('source_folder')):
            consume = sum(getsize(join(root, name)) \
                for name in files) / (2 ** 20)
            log.info(root + 'consumes' + str(consume) + 'M in' +
                str(len(files)) + 'non-directory files')
            for curr_file in files:
                if self.cmd_line.args.get('verbose'):
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
        '''Get/convert current file extension'''
        try:
            name, extension = curr_file.rsplit('.', 1)
        except ValueError, ex:
            log.error('No Extension')
            return ''
        except Exception, ex:
            log.error(('Unknown Error', ex))
        extension = '.' + extension
        if self.cmd_line.args.get('lower_case_ext'):
            extension = extension.lower()
        return extension

    def _extract_tags(self, tags):
        return tags

    def _get_MakerNoteTotalShutterReleases(self, curr_file, tags):
        try:
            mtsr = tags.get('MakerNote TotalShutterReleases').values[0]
        except AttributeError, ex:
            log.error(('Attribute error', ex, curr_file))
            if not self.cmd_line.args.get('queue_errors'):
                sys.exit(1)
            return ''
        except Exception, ex:
            log.error(('Error', ex, curr_file))
            if not self.cmd_line.args.get('queue_errors'):
                sys.exit(1)
            else:
                raise
        return '-%d' % mtsr

    def _format_filename(self, curr_file, tags):
        '''Format time'''

#        for (k, v) in tags.iteritems():
#            if ('MakerNote' in k) and ('Shutter' in k):
#                print (k, v)

        try:
            self.dto_str = tags.get('EXIF DateTimeOriginal').values
        except AttributeError, ex:
            log.error(('Attribute error', ex, curr_file))
            if not self.cmd_line.args.get('queue_errors'):
                sys.exit(1)
            else:
                raise Exception("Skip")
                sys.exit()
        except Exception, ex:
            log.error(('Error', ex, curr_file))
            if not self.cmd_line.args.get('queue_errors'):
                sys.exit(1)
            else:
                raise

        self.dto['MakerNoteTotalShutterReleases'] = self._get_MakerNoteTotalShutterReleases(curr_file, tags)
        self.dto['date'], self.dto['time'] = self.dto_str.split(' ')
        self.dto['YYYY'], self.dto['MM'], self.dto['DD'] = \
            self.dto['date'].split(':')
        self.dto['HH'], self.dto['mm'], self.dto['SS'] = \
            self.dto['time'].split(':')
        #self.dto['SST'] = self.sst_str
        self.new_name = RENAME_FORMAT % self.dto
        self.new_name = self.new_name + self._get_extension(curr_file)

    def _queue_quit(self):
        if not self.cmd_line.args.get('queue_errors'):
            sys.exit(1)

    def _format_dirname(self, curr_dir, tags):
        self.organized_dir = join(self.cmd_line.args.get('organized_dir'),
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
            self._process_current_do(curr_file)
            self._move_current()
        except Exception, ex:
            log.error(('Skipped rename', self.target, ex))

    def _process_current_do(self, curr_file):
        if not self.cmd_line.args.get('dry_run'):
            try:
                os.rename(curr_file, self.target)
            except Exception, ex:
                log.error(('Rename Failed', ex))
                if not self.cmd_line.args.get('queue_errors'):
                    sys.exit(1)
                else:
                    raise

    def _move_current(self):
        '''Move file'''
        log.debug(('curr_file_move', self.target,
            join(self.organized_dir, self.new_name)))

        log.debug('Creating target dir')
        if not self.cmd_line.args.get('dry_run'):
            try:
                os.makedirs(self.organized_dir)
            except Exception, (errno, ex):
                if errno in [17]:
                    pass
                else:
                    log.critical(('makedirs failed', errno, ex))
                    sys.exit(2)

        if not self.cmd_line.args.get('dry_run'):
            try:
                shutil.move(self.target, self.organized_dir)
            except shutil.Error as exc:
                if 'already exists' in str(exc):
                    if self.cmd_line.args.get('overwrite'):
                        if filecmp.cmp(self.target,
                            join(self.organized_dir, self.new_name)):
                            if self.cmd_line.args.get('delete_dupes'):
                                try:
                                    os.remove(self.target)
                                except Exception, ex:
                                    log.critical((self.target, ex))
                                    sys.exit()
                        else:
                            log.error((self.target, 'and',
                                join(self.organized_dir, self.new_name),
                                'differ'))
                            self._queue_quit()
                    else:
                        log.warn(exc)
            except Exception as exc:
                log.error(('move failed', exc))
                self._queue_quit()
            else:
                log.debug('Moved %s to %s' % (self.target, join(self.organized_dir, self.new_name)))

class CompressedMirror(object):
    '''Maintain a compressed mirror for easily uploading'''

    def __init__(self, cmd_line):
        self.cmd_line = cmd_line
        self.compressed_mirror = self.cmd_line.args.get('compressed_mirror')
        self._setup_path(self.compressed_mirror)
        self.size = (self.cmd_line.args.get('compressed_dimension'),
                self.cmd_line.args.get('compressed_dimension'))
        log.debug('size: ' + str(self.size))
        self._walk()

    def _setup_path(self, path):
        log.debug('begin')
        try:
            os.makedirs(path)
        except Exception as ex:
            if not ex.errno == EEXIST:
                log.critical('Cannot make compressed mirror target: %s' % ex)
                sys.exit()
        log.debug('end')

    def _walk(self):
        '''Walk the path'''
        log.debug('begin')
        log.debug('organized_dir:' + self.cmd_line.args.get('organized_dir'))
        for root, dirs, files in os.walk(self.cmd_line.args.get('organized_dir')):
            consume = sum(getsize(join(root, name)) \
                for name in files) / (2 ** 20)
            log.info(root + 'consumes' + str(consume) + 'M in' +
                str(len(files)) + 'non-directory files')
            for curr_file in files:
                if self.cmd_line.args.get('verbose'):
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
                        self._compress_current(root, curr_file)

    def _compress_current(self, root, curr_file):
        postfix = '--%sx.jpg' % self.cmd_line.args.get('compressed_dimension')
        sliced_root = root[len(self.cmd_line.args.get('organized_dir'))+1:]
        target_path = join(self.compressed_mirror, sliced_root)
        target_file = join(target_path, curr_file[:-4] + postfix)
        source_image = join(root, curr_file)
        #log.debug(('root', sliced_root))
        #log.debug(('target_path', target_path))
        #log.debug(('curr_file', curr_file))
        #log.debug(('target_file', target_file))
        self._setup_path(target_path)
        if exists(target_file):
            if self.cmd_line.args.get('overwrite'):
                log.debug('Overwriting: %s'  % target_file)
                self._write_file(source_image, target_file)
            else:
                log.debug('Not overwriting: %s' % target_file)
        else:
            log.debug('Writing: %s' % target_file)
            self._write_file(source_image, target_file)
        #log.debug(('source_image', source_image))

    def _write_file(self, source_image, target_file):
        if self.cmd_line.args.get('dry_run'):
            return
        try:
            source_img = Image.open(source_image)
            target_img = source_img.copy()
            target_img.thumbnail(self.size, Image.ANTIALIAS)
            target_img.save(target_file)
        except Exception as ex:
            log.error(('error', target_file, ex))


def main():
    '''Run everything'''

    cmd_line = CommandLineParameters()
    if not cmd_line.skip_processfiles:
        ProcessFiles(cmd_line)
    if cmd_line.args.get('compressed_mirror'):
        print 'Compress Mirror'
        CompressedMirror(cmd_line)


if __name__ == "__main__":
    main()
