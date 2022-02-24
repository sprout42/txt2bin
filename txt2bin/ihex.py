import enum
import struct

import logging
logger = logging.getLogger(__name__)

__all__ = [
    'parse',
]


class IHEX_CODE(enum.IntEnum):
    DATA = 0
    EOF = 1
    EXT_SEG_ADDR = 2
    START_SEG_ADDR = 3
    EXT_LINEAR_ADDR = 4
    START_LINEAR_ADDR = 5


def checksum(data, init=0):
    val = init
    for i in range(len(data)):
        val = (val + data[i]) & 0xFF
    return val


IHEX_LINE_STRUCT = struct.Struct('>BHB')
IHEX_ADDR_STRUCT = struct.Struct('>H')
IHEX_SEG_STRUCT = struct.Struct('>HH')
IHEX_START_ADDR_STRUCT = struct.Struct('>I')


def parse(filename):
    offset = 0
    with open(filename, 'r') as f:
        linenum = 0
        for line in f.readlines():
            # Assume lines that don't start with ':' are comments
            if line[0] == ':':
                # convert the line to bytes (drop the ':' any trailing
                # whitespace)
                line = line.strip()
                line_data = bytes.fromhex(line[1:])

                # Validate the checksum
                if checksum(line_data) != 0:
                    raise ValueError('IHEX line %d checksum error: %s' % \
                            (linenum, line))

                size, addr, code = IHEX_LINE_STRUCT.unpack_from(line_data)

                # 4 bytes of header + 1 byte of checksum
                if len(line_data) != size + 5:
                    raise ValueError('IHEX line %d unexpected length: %s' % \
                            (linenum, line))

                # Determine if the data should be treated as bytes or an integer
                if code == IHEX_CODE.DATA:
                    yield (offset + addr, line_data[4:-1])

                elif code == IHEX_CODE.EOF:
                    logger.debug('%s', IHEX_CODE(code).name)
                    return

                elif code == IHEX_CODE.EXT_SEG_ADDR:
                    if size != 2:
                        raise ValueError('IHEX line %d segment address unexpected data size: %s' % \
                                (linenum, line))
                    base = IHEX_ADDR_STRUCT.unpack_from(line_data, 4)[0]
                    offset = base * 16
                    logger.debug('%s: 0x%04x -> 0x%08x', IHEX_CODE(code).name, base, offset)

                elif code == IHEX_CODE.START_SEG_ADDR:
                    cs, ip = IHEX_SEG_STRUCT.unpack_from(line_data, 4)[0]
                    offset = (cs * 16) + ip
                    base = IHEX_ADDR_STRUCT.unpack_from(line_data, 4)[0]
                    logger.debug('%s: 0x%04x, 0x%04x -> 0x%08x', IHEX_CODE(code).name, cs, ip, offset)

                elif code == IHEX_CODE.EXT_LINEAR_ADDR:
                    if size != 2:
                        raise ValueError('IHEX line %d segment address unexpected data size: %s' % \
                                (linenum, line))
                    base = IHEX_ADDR_STRUCT.unpack_from(line_data, 4)[0]
                    offset = base << 16
                    logger.debug('%s: 0x%04x -> 0x%08x', IHEX_CODE(code).name, base, offset)

                elif code == IHEX_CODE.START_LINEAR_ADDR:
                    offset = IHEX_START_ADDR_STRUCT.unpack_from(line_data, 4)[0]
                    logger.debug('%s: 0x%08x', IHEX_CODE(code).name, offset)

            linenum += 1
