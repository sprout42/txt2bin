import enum
import shutil
import argparse
import operator
import collections

from . import ihex, srec


__all__ = [
    'txt2bin',
    'ihex2bin',
    'srec2bin',
]


class TXT2BIN_FILETYPE(enum.Enum):
    AUTO = 'auto'
    IHEX = 'ihex'
    SREC = 'srec'


def guess_filetype(filename):
    # Use the first character of each line to identify if this is more
    # likely an srec or ihex file
    with open(filename, 'r') as f:
        first_chars = collections.Counter(l[0] for l in f)

        # Simple heuristic to detect file type, if it's srec then 'S' should
        # be the most likely character to appear, for ihex it should be ':'
        chars = [c for c, v in reversed(sorted(first_chars.items(), key=operator.itemgetter(1)))]
        if chars[0] == ':':
            return TXT2BIN_FILETYPE.IHEX
        elif chars[0] == 'S':
            return TXT2BIN_FILETYPE.SREC
        else:
            raise ValueError('Cannot guess filetype for %s. Most common chars: %s' % \
                    (filename, ', '.join(chars)))


def parse(filename, filetype=TXT2BIN_FILETYPE.AUTO):
    if isinstance(filetype, TXT2BIN_FILETYPE):
        typ = filetype
    else:
        try:
            typ = TXT2BIN_FILETYPE(filetype)
        except ValueError:
            typ = None

    if typ == TXT2BIN_FILETYPE.AUTO:
        typ = guess_filetype(filename)

    if typ == TXT2BIN_FILETYPE.IHEX:
        parsed = ihex.parse(filename)
    elif typ == TXT2BIN_FILETYPE.SREC:
        parsed = srec.parse(filename)
    else:
        options = ', '.join(t.value for t in list(TXT2BIN_FILETYPE))
        raise ValueError('Filetype %s not supported, must be one of %s' % \
                (filetype, options))


def parsed2bin(parsed):
    # Sort the data into chunks and return an offset + data for each chunk
    chunks = {}
    offset_to_base = {}

    for offset, data in parsed:
        if offset not in offset_to_base:
            chunks[offset] = bytearray(data)
            offset_to_base[offset+len(data)] = offset
        else:
            base = offset_to_base[offset]
            chunks[base] += data
            del offset_to_base[offset]
            offset_to_base[base+len(data)] = base

    return tuple((b, c) for b, c in sorted(chunks.items()))


def txt2bin(filename, filetype):
    parsed = parse(filename, filetype)
    return parsed2bin(parsed)


def ihex2bin(filename):
    parsed = parse(filename, 'ihex')
    return parsed2bin(parsed)


def srec2bin(filename):
    parsed = parse(filename, 'srec')
    return parsed2bin(parsed)


def write(filename, parsed, base=0):
    if isinstance(filename, str):
        # Open the file
        f = open(filename, 'wb')

        # First truncate the output file so we don't accidentally mix bad values
        # from a previous run
        f.truncate(0)
    else:
        # Otherwise assume the filename argument is an already opened file
        # handle
        f = filename

    for offset, data in parsed:
        # Adjust all file offsets to be relative to the supplied base
        # address (so if a file is intended to be offset by 0x00800000 then
        # an offset of 0x00810000 would cause a seek to 0x00010000.
        f.seek(offset - base)
        f.write(data)

    f.close()


def merge(filename, origfile, parsed, base=0):
    # copy the origfile file to the output
    shutil.copyfile(origfile, filename)

    # Open the new file now so the write() function doesn't truncate it
    with open(filename, 'wb') as f:
        write(f, parsed, base)


def main():
    type_choices = [t.value for t in list(TXT2BIN_FILETYPE)]
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--base', default=0,
            help='default output file offset (should normally just be 0)')
    parser.add_argument('-m', '--merge-with', default=None,
            help='existing binary to merge the xcal with')
    parser.add_argument('-t', '--type', default='auto',
            choices=type_choices, help='input file type')
    parser.add_argument('input', help='input xcal filename')
    parser.add_argument('output', help='output binary filename')

    args = parser.parse_args()

    parsed = txt2bin.parse(args.input, args.type)
    if args.merge_with:
        txt2bin.write(args.output, args.merge_with, parsed, base=args.base)
    else:
        txt2bin.write(args.output, parsed, base=args.base)
