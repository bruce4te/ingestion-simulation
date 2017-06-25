# ingestion-simulation
Simulates distributed, parallel ingestion and processing of assets (PDFs) based on queues (reception, creation, processing).

All ingestion and processing "tasks" run in threads processing common queues and create associated MongoDB and 
Elasticsearch documents. The goal is to simulate the upload of assets to an app cluster, reception of those assets,
parallel processing of those assets on another app cluster, and finalization of the process on the receiving app cluster.  
  
## Installation
The simulation is based on Python 2.7.11. 
1. If not already available install [pip](https://packaging.python.org/tutorials/installing-packages/#install-pip-setuptools-and-wheel)
2. Install virtualenv: `pip install virtualenv`
3. Clone this repository
4. cd to the cloned repository where requirements.txt is located.
5. activate your virtualenv.
6. run: `pip install -r requirements.txt` in your shell.