import shutil
import operator
import collections

from . import ihex, srec


__all__ = [
    'txt2bin',
    'ihex2bin',
    'srec2bin',
]


TXT2BIN_FILETYPES = ('auto', 'ihex', 'srec')


def guess_filetype(filename):
    # Use the first character of each line to identify if this is more
    # likely an srec or ihex file
    with open(filename, 'r') as f:
        first_chars = collections.Counter(l[0] for l in f)

        # Simple heuristic to detect file type, if it's srec then 'S' should
        # be the most likely character to appear, for ihex it should be ':'
        chars = [c for c, v in reversed(sorted(first_chars.items(), key=operator.itemgetter(1)))]
        if chars[0] == ':':
            return 'ihex'
        elif chars[0] == 'S':
            return 'srec'
        else:
            raise ValueError('Cannot guess filetype for %s. Most common chars: %s' % \
                    (filename, ', '.join(chars)))


def parse(filename, filetype):
    if filetype == 'auto':
        filetype = guess_filetype(filename)

    if filetype == 'ihex':
        parsed = ihex.parse(filename)
    elif filetype == 'srec':
        parsed = srec.parse(filename)
    else:
        raise ValueError('Filetype %s not supported, must be one of %s' % \
                (filetype, ', '.join(TXT2BIN_FILETYPES)))


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
