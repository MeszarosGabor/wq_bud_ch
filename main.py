"""
    Main Runner of the BiddingServer.
"""
import logging
import sys

from rpyc.utils.server import ThreadedServer
from server import BiddingService

logger = logging.getLogger()
logger.setLevel(logging.INFO)
loghandler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('[%(levelname)s] - %(asctime)s: %(message)s',
                              datefmt='%Y-%m-%d %H:%M:S')
loghandler.setFormatter(formatter)
logger.addHandler(loghandler)


s = ThreadedServer(BiddingService(bid_window_sec=5),
                   port=18871,
                   protocol_config={"allow_all_attrs": True})
print("Starting rpyc BiddingService...")
s.start()
