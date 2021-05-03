from client import BiddingClient
from time import sleep

host = 'localhost'
port = 18871
client1 = BiddingClient(host, port, 123)
client2 = BiddingClient(host, port, 124)

for _ in range(3):
    client1.submit_bid('up')
    print(client1.get_bid_info(client1.my_bids[-1].submission_id))
    #client1.submit_bid('up')
    #client2.submit_bid('up')
    client2.submit_bid('down')
    for _ in range(2):
        sleep(10)
        print(client1.get_bid_info(client1.my_bids[-1].submission_id))
        print(client2.get_bid_info(client2.my_bids[-1].submission_id))

print("user id: ", client1.client_id, ", score:", client1.get_score())
print("user id: ", client2.client_id, ", score:", client2.get_score())
