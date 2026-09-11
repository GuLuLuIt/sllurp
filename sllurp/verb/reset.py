"""Reset command."""


from sllurp.llrp import LLRPReaderClient, LLRPReaderConfig, LLRPReaderState
from sllurp.log import get_logger
from sllurp.util import split_host_port

logger = get_logger(__name__)


def shutdown(reader, state):
    host, port = reader.get_peername()
    logger.info("Shutting down reader %s:%d", host, port)
    reader.disconnect()


def main(args):
    if not args.host:
        logger.info("No readers specified.")
        return 0

    factory_args = {
        "start_inventory": False,
        "reset_on_connect": False,
        "tls_enabled": args.tls_enabled,
        "tls_verify": args.tls_verify,
        "tls_ca_file": args.tls_ca_file,
        "tls_client_cert": args.tls_client_cert,
        "tls_client_key": args.tls_client_key,
        "tls_server_hostname": args.tls_server_hostname,
    }

    reader_clients = []
    for host_value in args.host:
        host, port = split_host_port(host_value, args.port)

        config = LLRPReaderConfig(factory_args)
        reader = LLRPReaderClient(host, port, config, timeout=3)
        reader.add_state_callback(LLRPReaderState.STATE_CONNECTED, shutdown)
        # FYI, the reader connection is really finished and idle in the state
        # STATE_SENT_SET_CONFIG just before inventory because of the big state
        # machine. But for "reset", stopping after STATE_CONNECTED is enough
        reader_clients.append(reader)

    for reader in reader_clients:
        host, port = reader.get_peername()
        try:
            reader.connect()
        except Exception:
            logger.error("Failed to connect to %s:%d. Skipping...", host, port)

    while True:
        try:
            # Join all threads using a timeout so it doesn't block
            # Filter out threads which have been joined or are None
            alive_readers = [reader for reader in reader_clients if reader.is_alive()]
            if not alive_readers:
                break
            for reader in alive_readers:
                reader.join(1)
        except (KeyboardInterrupt, SystemExit):
            # catch ctrl-C and stop inventory before disconnecting
            logger.info("Exit detected! Stopping readers...")
            for reader in reader_clients:
                try:
                    reader.disconnect()
                except Exception:
                    logger.exception("Error during disconnect. Ignoring...")
