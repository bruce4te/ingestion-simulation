import time
import datetime
import random
from threading import Thread
from Queue import Queue
from elasticsearch import Elasticsearch, ConnectionTimeout
from pymongo import MongoClient, ReturnDocument
from optparse import OptionParser
from multiprocessing import freeze_support

from pymongo.errors import DuplicateKeyError

INDEX_PREFIX = 'test-ingestion'
CONTENT_COLLECTION = 'content'
INDEX_NAME = "-".join([INDEX_PREFIX, datetime.datetime.utcnow().strftime('%Y-%m-%d')])
COUNT_CREATORS = 5
COUNT_PROCESSORS = 5

reception_queue = Queue()
creation_queue = Queue()
processed_queue = Queue()
log_queue = Queue()
mongodb_uri = None
es = None


def main():
    # handle command line args
    parser = OptionParser()
    parser.add_option("-d", action="store_true", dest="dryrun", help="dry_run true")
    parser.add_option("-n", "--number", dest="number_simulations", help="number of simulations")
    parser.add_option("-e", "--eshosts", dest="es_hosts_string", help="elasticsearch hosts:port string")
    parser.add_option("-s", "--start_index", dest="start_index", type=int)

    (options, args) = parser.parse_args()
    dry_run = options.dryrun
    number_simulations = options.number_simulations
    es_hosts_string = options.es_hosts_string
    start_index = options.start_index

    if dry_run is None:
        dry_run = False
    if number_simulations is None:
        print "--number is required"
    if es_hosts_string is None:
        print "--eshosts is required"
    if start_index is None:
        start_index = 0

    set_es_hosts(es_hosts_string)

    read_mongodb_uri()

    print "Ingestion started"
    receiver1 = Thread(target=upload_assets, kwargs={'host_name': "upload1",
                                                     'assets_to_upload': long(number_simulations),
                                                     'start_index': start_index})
    receiver1.start()

    creators = []
    for i in range(COUNT_CREATORS):
        creators.append(Thread(target=receive_assets, kwargs={'host_name': "".join(["creator", str(i)])}))
    for creator in creators:
        creator.start()

    processors = []
    for i in range(COUNT_PROCESSORS):
        processors.append(Thread(target=process_assets, kwargs={'host_name': "".join(["processor", str(i)])}))
    for processor in processors:
        processor.start()


def upload_assets(host_name, assets_to_upload, start_index):
    global reception_queue
    for asset in range(start_index, start_index + assets_to_upload):
        file_name = "".join(["content/", ('{:06d}'.format(asset)), ".pdf"])
        reception_queue.put(file_name)
        time1 = datetime.datetime.utcnow()
        log_action("File uploaded", host_name, file_name, time1)
    for i in range(COUNT_CREATORS):
        reception_queue.put('STOP')
    print "Reception finished"


def receive_assets(host_name):
    global reception_queue, creation_queue
    content_collection = setup_content_connection()
    for file_name in iter(reception_queue.get, 'STOP'):
        subs = random.randrange(1, 5)
        size = random.randrange(3000000, 7000000)
        time.sleep((size/10000000))
        create_asset(content_collection, host_name, file_name, size)
        if subs % 2 == 0:
            create_asset(content_collection, host_name, file_name + "/page1.pdf", long(size * 0.6))
            create_asset(content_collection, host_name, file_name + "/page2.pdf", long(size*0.4))
        else:
            create_asset(content_collection, host_name, file_name + "/page1.pdf", long(size * 0.99))
    creation_queue.put('STOP')
    print "Creation finished: " + host_name


def create_asset(content_collection, host_name, file_name, size):
    global creation_queue
    start = datetime.datetime.utcnow()
    result = create_repo_entry(file_name, content_collection, size)
    if result is not None:
        log_action("File received and stored", host_name, file_name, start)
        creation_queue.put(file_name)


def process_assets(host_name):
    global creation_queue, processed_queue
    content_collection = setup_content_connection()
    for file_name in iter(creation_queue.get, 'STOP'):
        start = datetime.datetime.utcnow()
        update_repo_entry(file_name, content_collection)
        log_action("Start processing", host_name, file_name, start)
        time.sleep(random.uniform(0.3, 0.6))
        update_repo_entry(file_name, content_collection)
        end = datetime.datetime.utcnow()
        td = end - start
        log_action("Finished processing", host_name, file_name, end,
                   int(td.microseconds / 1000))
        processed_queue.put(file_name)
    processed_queue.put('STOP')
    print "Processing finished: " + host_name


def log_queues(host_name):
    time.sleep(1)
    global reception_queue, creation_queue, processed_queue
    print "\t".join(["Reception:", str(reception_queue.qsize()), "Creation:", str(creation_queue.qsize()),
                     "Processing:", str(processed_queue.qsize())])
    time.sleep(10)


def setup_content_connection():
    global mongodb_uri
    mongodb_client = MongoClient(mongodb_uri)
    return mongodb_client["repository"].get_collection(CONTENT_COLLECTION)


def read_mongodb_uri():
    global mongodb_uri
    try:
        uri_file = open("mongodb_uri.txt", "r+")
        mongodb_uri = uri_file.readline()
        uri_file.close()
    except IOError:
        print "Couldn't load file mongodb_uri.txt"


def set_es_hosts(es_hosts_string):
    global es
    es_hosts = str.split(es_hosts_string, ":")
    es = Elasticsearch(str.split(es_hosts[0], ","), port=es_hosts[1])


def create_repo_entry(_id, content_collection, size):
    file_parts = str(_id).split(".")
    file_type = file_parts[-1]
    if len(file_parts) > 2:
        file_type = "subasset/pdf"
    try:
        result = content_collection.insert_one({"_id": _id, "type": file_type, "size": size, "created": datetime.datetime.utcnow(),
                                                "modified": datetime.datetime.utcnow()})
        return result.inserted_id
    except DuplicateKeyError:
        print "duplicate key error inserting doc with _id " + _id
        return None


def update_repo_entry(_id, content_collection):
    content_collection.find_one_and_update({'_id': _id}, {'$set': {'modified': datetime.datetime.utcnow()}},
                                           return_document=ReturnDocument.AFTER)


def log_action(action, host, file_name, start, time_spent=None):
    global es
    doc = {'action': action, 'processInstance': "/".join(["instances", host, str(long(time.time() * 1000))]),
           'processItem': file_name, 'host': host,
           '@timestamp':
               "".join([str.replace(start.strftime('%Y-%m-%d_%H:%M:%S.%f')[:-3], "_", "T"), "Z"])}
    if time_spent is not None:
        doc['timeSpent'] = time_spent
    try:
        es.index(index=INDEX_NAME, doc_type='asset_content', body=doc)
    except ConnectionTimeout:
        print "Timed out: " + file_name


if __name__ == '__main__':
    freeze_support()
    main()
