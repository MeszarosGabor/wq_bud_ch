# wq_bud_ch
This is a bare-bone implementation of the challenge with a server and client
class and minimalistic testing provided. Time invested: ~8-9 eng. hours.

Additional features, good-to-have items that stuck out to me during the work:
- user registry; client authentication
- unit test coverage
- high QPS support through parallelism
- DB support, DR features added
- logging support, log rotation/discarding
- custom interval bids (today the server automatically places the bid on the next available interval)
- bid amount handling. Pairing based on the same amounts. Odds handling
- linking real life datasources
- adding various underlying assets. 
