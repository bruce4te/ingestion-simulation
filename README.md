# ingestion-simulation
Simulates distributed, parallel ingestion and processing of assets (PDFs) based on queues (reception, creation, processing).

All ingestion and processing "tasks" run in threads processing common queues and create associated MongoDB and 
Elasticsearch documents. The goal is to simulate the upload of assets to an app cluster, reception of those assets
by this cluster, parallel processing of those assets on a different, remote app cluster, and final processing on the receiving app cluster.  
  
## Installation
The simulation is based on Python 2.7.11. 
* If not already available install [pip](https://packaging.python.org/tutorials/installing-packages/#install-pip-setuptools-and-wheel)
* Install virtualenv: `pip install virtualenv`
* Clone this repository
* cd to the cloned repository directory where `requirements.txt` is located
* Create a virtualenv named `venv` via `virtualenv venv`
* cd to the `venv` directory
* activate your virtualenv (e.g. `$ source bin/activate`)
* run: `pip install -r requirements.txt` in your shell
* add a `mongodb_uri.txt` file to the directory with a single line:

    `mongodb://[username:password@]host1[:port1][,host2[:port2],...[,hostN[:portN]]][/[database][?options]]`

   where you replace the placeholders with corresponding real values.
* run the command:

    `curl -XPUT 'http://<es-host>:<es-port>/_template/template_ingestion' -d@template_ingestion.json`
    
   where `<es-host>` is your elastic server IP or hostname (e.g. localhost) and `<es-port>` the corresponding port (e.g. 9200)
     
## Run the ingestion

From the directory where the `threaded_ingestion.py` file is located, run:

`python threaded_ingestion.py -n 10 -e <es-host1>,<es-host2>:<es-port> -s 0`
 
 where `-n` defines the number of "files" ingested, `-e` serves as es connection string (comma separated list of hosts:port), 
 and the `-s` option lets you define a start index for the file names (e.g. 0 -> 000000.pdf as first file).   