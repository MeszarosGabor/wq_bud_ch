"""
A Simple RPyC Bidding Server implementation.
"""

import logging
import random
import time
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime
from threading import Thread, RLock

from rpyc import Service


logger = logging.getLogger(__name__)


class Bid:
    """ Bid class addressing the change of the underlying asset in the next
        time window.
    """
    def __init__(self, user_id, change, submission_time,
                 submission_id, period_start, period_end):
        self.user_id = user_id
        self.change = change
        self.submission_time = submission_time
        self.submission_id = submission_id
        self.period_start = period_start
        self.period_end = period_end

    def __repr__(self):
        return "Bid(\n" + "\n".join([f'{k}: {v}' for k, v in self.__dict__.items()]) + "\n)"


class BiddingService(Service):
    """ Bidding Services serving bid requests and result lookups. """
    def __init__(self, bid_window_sec):
        super().__init__()

        self.bid_window_sec = bid_window_sec
        self.thread_sleep_sec = 1

        self.all_time_bid_ids = set()
        self.all_time_paired_bid_ids = set()
        self.unpaired_bids = []
        self.bid_pairs = []
        self.last_submission_id = 0

        self.lost_bid_ids = set()
        self.won_bid_ids = set()
        self.user_scores = defaultdict(int)

        self.rlock = RLock()

        self.rates = {}

        self.rate_thread = Thread(target=self.fetch_rates, args=())
        self.eval_thread = Thread(target=self.evaluate_bid_pairs, args=())

        self.start_service_threads()

    def start_service_threads(self):
        logger.info("Starting rate thread...")
        self.rate_thread.start()
        logger.info("Starting eval thread...")
        self.eval_thread.start()

    def __del__(self):
        self.rate_thread.join()
        self.eval_thread.join()

    def on_connect(self, conn):
        logger.info('Client connected!')

    ############################# RATE MANAGEMENT #############################
    def fetch_rates(self):
        """ Util function to collect data about the underlying asset. """
        while True:
            t = datetime.now()
            logger.debug(f"Checking rate thread at time {t}")
            tt = datetime(t.year, t.month, t.day, t.hour, t.minute, t.second)
            rate = self.get_exchange_rate()
            self.rates[tt] = rate
            logger.debug(f"Recorded rate {rate} at {tt}")
            time.sleep(self.thread_sleep_sec)

    # TODO: apply actual data fetching here.
    def get_exchange_rate(self, *args, **kwrags):
        """ This function return the exchange rate related to the asset. """
        return random.random()

    def _take_closest(self, bid_time):
        """
        Assumes rate_times are sorted. Returns closest timestamp to bid_time.
        If two numbers are equally close, return the smallest number.
        """
        rate_times = list(self.rates.keys())
        pos = bisect_left(rate_times, bid_time)
        if pos == 0:
            return rate_times[0]
        if pos == len(rate_times):
            return rate_times[-1]
        before = rate_times[pos - 1]
        after = rate_times[pos]
        if after - bid_time < bid_time - before:
            return after
        else:
            return before

    ########################### BID SUBMISSION ################################
    def generate_submission_id(self):
        self.last_submission_id += 1
        return self.last_submission_id

    def get_next_bid_window_start(self, t):
        return datetime.fromtimestamp(
            (int(t.timestamp()) //
             self.bid_window_sec + 1) * self.bid_window_sec)
    
    def get_next_bid_window_end(self, t):
        return datetime.fromtimestamp(
            (int(t.timestamp()) //
             self.bid_window_sec + 2) * self.bid_window_sec)

    ########################### BID MATCH/EVAL ################################
    def match_or_queue_bid(self, new_bid):
        for i in range(len(self.unpaired_bids)):
            if self.unpaired_bids[i].user_id != new_bid.user_id and\
                    self.unpaired_bids[i].change != new_bid.change and\
                    self.unpaired_bids[i].period_start == new_bid.period_start:
                self.bid_pairs.append((self.unpaired_bids[i], new_bid))
                logger.info(f"paired {self.unpaired_bids[i]} and {new_bid}")
            
                self.all_time_paired_bid_ids.add(new_bid.submission_id)
                self.all_time_paired_bid_ids.add(self.unpaired_bids[i].submission_id)
                self.unpaired_bids.pop(i)
                break
        else:
            logger.info(f"Could not immediately pair bid {new_bid}, adding to queue")
            self.unpaired_bids.append(new_bid)

    def evaluate_bid_pair(self, pair):
        start_rate = self.rates.get(self._take_closest(pair[0].period_start))
        end_rate = self.rates.get(self._take_closest(pair[0].period_end))
        if not start_rate or not end_rate:
            logger.error(f"Rate at start {pair[0].period_start} should exist, "
                  f"got {start_rate}")
            logger.error(f"Rate at end {pair[0].period_end} should exist, "
                  f"got {end_rate}")
        higher = [item for item in pair if item.change == 'up'][0]
        lower = [item for item in pair if item.change == 'down'][0]
        winner = higher if end_rate > start_rate else lower
        loser = higher if end_rate <= start_rate else lower

        self.won_bid_ids.add(winner.submission_id)
        self.lost_bid_ids.add(loser.submission_id)
        self.user_scores[winner.user_id] += 1
        self.user_scores[loser.user_id] -= 1
        logger.info(f"Winner of bid {pair} is {winner}")

    def evaluate_bid_pairs(self):
        while True:
            t = datetime.now()
            logger.debug(f"Checking bid pairs at time {t}")
            ready_pairs = [pair for pair in self.bid_pairs if
                           pair[0].period_end < t]
            logger.info(f"Pairs ready to be evaluated: {ready_pairs}")
            for pair in ready_pairs:
                self.evaluate_bid_pair(pair)
            self.bid_pairs = list(set(self.bid_pairs) - set(ready_pairs))
            time.sleep(self.thread_sleep_sec)

    ########################## EXPOSED FUNCTIONS ##############################
    def exposed_submit_bid(self, user_id, change):
        if change not in ['up', 'down']:
            return None
        t = datetime.now()
        bid = Bid(
            user_id=user_id,
            change=change,
            submission_time=t,
            submission_id=self.generate_submission_id(),
            period_start=self.get_next_bid_window_start(t),
            period_end=self.get_next_bid_window_end(t)
        )
        self.all_time_bid_ids.add(bid.submission_id)
        logger.info(f"Bid Submitted: {bid}")
        logger.debug(f'Bids in system: {self.unpaired_bids}')
        with self.rlock:
            self.match_or_queue_bid(bid)
        return bid

    def exposed_get_bid_info(self, submission_id):
        logger.info(f"Getting info for submission id {submission_id}")
        if submission_id in self.won_bid_ids:
            return f"Congrats, you have won the bid with id {submission_id}"
        elif submission_id in self.lost_bid_ids:
            return f"You lost the bid with id {submission_id}, better luck next time"
        elif submission_id in self.all_time_paired_bid_ids:
            return f"Your bid with id {submission_id} has been paired up, awating evaluation."
        elif submission_id in [item.submission_id for item in self.unpaired_bids]:
            return f"Your bid with id {submission_id} has been received, awaiting pairing."
        else:
            return f"Hm, I have no idea where this bid with id {submission_id} is..."

    def exposed_get_user_score(self, user_id):
        return self.user_scores.get(user_id)
