"""
    Minimalistic Biddingclient implementation.
"""


import rpyc


class BiddingClient:

    def __init__(self, host, port, client_id):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.conn = rpyc.connect(host, port, config={"allow_all_attrs": True})
        self.my_bids = []

    def submit_bid(self, direction):
        bid = self.conn.root.submit_bid(self.client_id, direction)
        self.my_bids.append(bid)

    def get_bid_info(self, submission_id):
        return self.conn.root.get_bid_info(submission_id)

    def get_score(self):
        return self.conn.root.get_user_score(self.client_id)
