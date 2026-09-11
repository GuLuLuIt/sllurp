import argparse
import binascii
import logging

from sllurp.llrp import LLRPMessage

logger = logging.getLogger("sllurp")
args = None


def parse_args(argv=None):
    global args
    parser = argparse.ArgumentParser(description="Decode an LLRP message")
    parser.add_argument("msg", help="message in hexadecimal encoding")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args(argv)
    return args


def init_logging():
    log_level = logging.DEBUG if args.debug else logging.INFO
    log_format = "%(asctime)s %(name)s: %(levelname)s: %(message)s"
    formatter = logging.Formatter(log_format)
    stderr = logging.StreamHandler()
    stderr.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers = [stderr]


def main(argv=None):
    parsed = parse_args(argv)
    init_logging()
    message = LLRPMessage(msgbytes=binascii.unhexlify(parsed.msg))
    print("Decoded message:\n==========")
    print(message)


if __name__ == "__main__":
    main()
