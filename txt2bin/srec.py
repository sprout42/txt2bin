import enum
import struct

import logging
logger = logging.getLogger(__name__)

__all__ = [
    'parse',
]


class SREC_CODE(enum.IntEnum):
    HEADER = 0
    DATA_16BIT_ADDR = 1
    DATA_24BIT_ADDR = 2
    DATA_32BIT_ADDR = 3
    #RESERVED = 4
    COUNT_16BIT = 5
    COUNT_24BIT = 6
    START_ADDR_32BIT = 7
    START_ADDR_24BIT = 8
    START_ADDR_16BIT = 9

SREC_DATA = (
    SREC_CODE.DATA_16BIT_ADDR,
    SREC_CODE.DATA_24BIT_ADDR,
    SREC_CODE.DATA_32BIT_ADDR,
)

SREC_COUNT = (
    SREC_CODE.COUNT_16BIT,
    SREC_CODE.COUNT_24BIT,
)

SREC_START_ADDR = (
    SREC_CODE.START_ADDR_32BIT,
    SREC_CODE.START_ADDR_24BIT,
    SREC_CODE.START_ADDR_16BIT,
)



# Precalculated shifts and ranges for different address sizes:
SREC_ADDR_RANGES = {
    SREC_CODE.HEADER: range(1, 3),
    SREC_CODE.DATA_16BIT_ADDR: range(1, 3),
    SREC_CODE.DATA_24BIT_ADDR: range(1, 4),
    SREC_CODE.DATA_32BIT_ADDR: range(1, 5),
    SREC_CODE.COUNT_16BIT: range(1, 3),
    SREC_CODE.COUNT_24BIT: range(1, 4),
    SREC_CODE.START_ADDR_32BIT: range(1, 3),
    SREC_CODE.START_ADDR_24BIT: range(1, 4),
    SREC_CODE.START_ADDR_16BIT: range(1, 5),
}

SREC_ADDR_SHIFTS = {
    SREC_CODE.HEADER: (8, 0),
    SREC_CODE.DATA_16BIT_ADDR: (8, 0),
    SREC_CODE.DATA_24BIT_ADDR: (16, 8, 0),
    SREC_CODE.DATA_32BIT_ADDR: (24, 16, 8, 0),
    SREC_CODE.COUNT_16BIT: (8, 0),
    SREC_CODE.COUNT_24BIT: (16, 8, 0),
    SREC_CODE.START_ADDR_32BIT: (8, 0),
    SREC_CODE.START_ADDR_24BIT: (16, 8, 0),
    SREC_CODE.START_ADDR_16BIT: (24, 16, 8, 0),
}


def checksum(data, init=0):
    val = init
    for i in range(len(data)):
        val = (val + data[i]) & 0xFFFF

    # the final SREC checksum value is the one's complement of the lowest byte
    # of the 2-byte accumulated sum
    return ~val & 0xFF


def get_addr(data, code):
    addr = 0
    for shift, idx in zip(SREC_ADDR_SHIFTS[code], SREC_ADDR_RANGES[code]):
        addr |= data[idx] << shift
    return addr


def parse(filename):
    with open(filename, 'r') as f:
        linenum = 0
        datacount = 0
        for line in f.readlines():
            # Assume lines that don't start with 'S' are comments
            if line[0] == 'S':
                code = SREC_CODE(int(line[1]))

                # convert the line to bytes (drop the 'S?' code and any trailing
                # whitespace)
                line = line.strip()
                line_data = bytes.fromhex(line[2:])

                # Validate the checksum
                if checksum(line_data) != 0:
                    raise ValueError('SREC line %d checksum error: %s' % \
                            (linenum, line))

                size = line_data[0]

                # SREC line size includes the address and checksum
                if len(line_data) != size + 1:
                    raise ValueError('SREC line %d unexpected length: %s' % \
                            (linenum, line))

                # Get the address/count value for this line
                addr = get_addr(line_data, code)

                # Parse each line
                if code == SREC_CODE.HEADER:
                    # Address should be 0
                    if addr != 0:
                        raise ValueError('SREC line %d unexpected header address value: %s' % \
                                (linenum, line))

                    data_start = SREC_ADDR_RANGES[code].stop
                    header = line_data[data_start:-1].decode()

                    logger.debug('%s: %s', code.name, header)

                elif code in SREC_DATA:
                    datacount += 1
                    data_start = SREC_ADDR_RANGES[code].stop
                    data = line_data[data_start:-1]
                    yield (addr, data)

                elif code in SREC_COUNT:
                    # Technically there should at most 1 count field, but this
                    # script doesn't enforce that
                    if addr != datacount:
                        raise ValueError('SREC line %d invalid count %d, should be %d: %s' % \
                                (linenum, addr, datacount, line))

                elif code == SREC_START_ADDR:
                    # The address is the entry point, and is also the last field
                    # in an SRecord
                    logger.debug('%s: 0x%x', code.name, addr)
                    return

            linenum += 1
