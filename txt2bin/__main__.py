import argparse
import txt2bin


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--base', default=0,
            help='default output file offset (should normally just be 0)')
    parser.add_argument('-m', '--merge-with', default=None,
            help='existing binary to merge the xcal with')
    parser.add_argument('-t', '--type', default='auto',
            choice=txt2bin.TXT2BIN_FILETYPES, help='input file type')
    parser.add_argument('input', help='input xcal filename')
    parser.add_argument('output', help='output binary filename')

    args = parser.parse_args()

    parsed = txt2bin.parse(args.input, args.type)
    if args.merge_with:
        txt2bin.write(args.output, args.merge_with, parsed, base=args.base)
    else:
        txt2bin.write(args.output, parsed, base=args.base)
