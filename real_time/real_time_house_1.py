from __future__ import print_function, division
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
import time
import time
from matplotlib import rcParams
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from six import iteritems
from nilmtk import DataSet, TimeFrame, MeterGroup, HDFDataStore
from nilmtk.legacy.disaggregate import CombinatorialOptimisation, FHMM
import nilmtk.utils
import time
import math
from datetime import datetime
from threading import Thread
import numpy.random
import requests

BUFFER_SIZE = 500
HOUSE = 1 
SERVER_IP = '172.31.63.90'
PORT = 7000

def erro_quadratico(predicao, referencia):
    erro = 0.0
    for i in range(len(predicao)):
        erro += (predicao[i] - referencia[i])**2
    return math.sqrt(erro/len(predicao))

def processa_dados(modelo, line):
    start = datetime.now()
    lista_pot = list()
    lista_index = list()
    for i in range(0,len(line)):
        time_stamp, potencia = line[i].split()
        print(time_stamp, potencia)
        time_stamp = int(time_stamp)
        lista_pot.append(float(potencia))
        dt_object = datetime.fromtimestamp(time_stamp)
        lista_index.append(dt_object)
    
      
    df = pd.DataFrame({'power apparent':lista_pot},
                   index = lista_index)
    predicao = modelo.disaggregate_chunk(df)
    predicao.columns = ['Geladeira', 'Cafeteira']
    list_geladeira = predicao['Geladeira'].tolist()
    list_cafeteira = predicao['Cafeteira'].tolist()

    pload1 = str(list_geladeira[len(list_geladeira)- 1])

    try:
        requests.post('http://unifeienergia.ml:1880/api/casa2/geladeira', data=pload1, timeout=0.0000001)
    except requests.exceptions.ReadTimeout: 
        pass

    pload2 = str(list_cafeteira[len(list_cafeteira) - 1])
    
    try:
        requests.post('http://unifeienergia.ml:1880/api/casa2/cafeteira', data=pload2, timeout=0.0000001)
    except requests.exceptions.ReadTimeout: 
        pass

    arquivo = open('geladeira_casa_1.txt', 'w')
    arquivo.write(str(list_geladeira[len(list_geladeira)-1])+'\n')
    arquivo.close()
    
    arquivo = open('cafeteira_casa_1.txt', 'w')
    arquivo.write(str(list_cafeteira[len(list_cafeteira)-1])+'\n')
    arquivo.close()

    end = datetime.now()
    elapsed = end - start
    print(elapsed.seconds,":",elapsed.microseconds) 
    
def predict(clf, test_elec, sample_period, timezone):
    pred = {}
    gt= {}

    for i, chunk in enumerate(test_elec.mains().load(sample_period=sample_period)):
        chunk_drop_na = chunk.dropna()
        pred[i] = clf.disaggregate_chunk(chunk_drop_na)
        gt[i]={}

        for meter in test_elec.submeters().meters:
            # Only use the meters that we trained on (this saves time!)
            gt[i][meter] = next(meter.load(sample_period=sample_period))
        gt[i] = pd.DataFrame({k:v.squeeze() for k,v in iteritems(gt[i]) if len(v)}, index=next(iter(gt[i].values())).index).dropna()

    # If everything can fit in memory
    gt_overall = pd.concat(gt)
    gt_overall.index = gt_overall.index.droplevel()
    pred_overall = pd.concat(pred)
    pred_overall.index = pred_overall.index.droplevel()


    # Having the same order of columns
    gt_overall = gt_overall[pred_overall.columns]

    #Intersection of index
    gt_index_utc = gt_overall.index.tz_convert("UTC")
    pred_index_utc = pred_overall.index.tz_convert("UTC")
    common_index_utc = gt_index_utc.intersection(pred_index_utc)


    common_index_local = common_index_utc.tz_convert(timezone)
    gt_overall = gt_overall.loc[common_index_local]
    pred_overall = pred_overall.loc[common_index_local]
    appliance_labels = [m for m in gt_overall.columns.values]
    gt_overall.columns = appliance_labels
    pred_overall.columns = appliance_labels

    return gt_overall, pred_overall


def convert(lst): 
    res_dct = {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)} 
    return res_dct

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'NILM-UNIFEI')

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        self.send_response(200)
        self.end_headers()
        response = BytesIO()
        response.write(b'This is POST request. ')
        response.write(b'Received: ')
        actual_time = time.time()

        if(len(buffer) >= BUFFER_SIZE):
            buffer.pop(0)
        buffer.append(str(int(actual_time)) + ' ' + body.decode('utf-8'))

        print(buffer)
        thread_processamento = Thread(target=processa_dados,args=(fhmm, buffer))
        thread_processamento.start()

        for b in buffer:
            response.write(b.encode())

        self.wfile.write(response.getvalue())

print("[OK] Carregando base de dados da casa: " + str(HOUSE))
buffer = []
train = DataSet('banco_unifei.h5')
#Enumera todas as casas
buildings = [ i for i in range(3)]
#Vetor que guarda os dados de todas as casas
train_elec = [None for i in range(3)]
for building in buildings:
    train_elec[building] = train.buildings[building+1].elec

print("[OK] Treinamento inicializado...")
numpy.random.seed(42)
sample_period = 120
predictions = []
gts = []
fhmm = FHMM()
fhmm.train(train_elec[0], sample_period=sample_period)

print("[OK] Processo de desagregacao iniciado...")
httpd = HTTPServer((SERVER_IP, PORT), SimpleHTTPRequestHandler)
print("[OK] Servidor HTTP Estabelecido com sucesso")
httpd.serve_forever()
