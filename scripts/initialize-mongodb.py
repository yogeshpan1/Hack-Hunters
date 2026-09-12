"""Initialize only the NEXUS local replica set; never reconfigure an existing server."""
import time
from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

client = MongoClient('mongodb://127.0.0.1:27017/?directConnection=true', serverSelectionTimeoutMS=1000)
deadline = time.monotonic() + 40
while True:
    try:
        client.admin.command('ping')
        break
    except PyMongoError:
        if time.monotonic() >= deadline: raise
        time.sleep(.5)
try:
    config = client.admin.command('replSetGetConfig')['config']
    if config['_id'] != 'nexus-rs':
        raise RuntimeError('Port 27017 belongs to another replica set. Set MONGODB_URI to your chosen server; no configuration was changed.')
except OperationFailure as exc:
    if exc.code != 94: raise
    client.admin.command('replSetInitiate', {'_id': 'nexus-rs', 'members': [{'_id': 0, 'host': '127.0.0.1:27017'}]})
while not client.admin.command('hello').get('isWritablePrimary'):
    if time.monotonic() >= deadline: raise RuntimeError('MongoDB did not elect a primary in time.')
    time.sleep(.5)
print('MongoDB is ready on 127.0.0.1:27017 (replica set nexus-rs).')
client.close()
