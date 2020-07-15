#Este projeto treina usando todas as casas e usando o método
from __future__ import print_function, division
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
from datetime import datetime
from threading import Thread
import numpy.random


from nilmtk.dataset_converters import convert_redd
#convert_redd(r'low_freq', 'redd.h5')

#Carrega os dados na memória
train = DataSet('redd.h5')
test = DataSet('redd.h5')

#Enumera todas as casas
buildings = [ i for i in range(6)]

# The dates are interpreted by Pandas, prefer using ISO dates (yyyy-mm-dd)
train.set_window(end="2011-04-30")
test.set_window(start="2011-04-30")

#Vetor que guarda os dados de todas as casas
train_elec = [None for i in range(6)]
test_elec = [None for i in range(6)]

for building in buildings:
    train_elec[building] = train.buildings[building+1].elec
    test_elec[building] = test.buildings[building+1].elec

#Seleciona as top 5 aplicações de cada casa
top_5_train_elec = [None for i in range(6)]

for building in buildings:
    top_5_train_elec[building] = train_elec[building].submeters().select_top_k(k=5)

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

entrada = open('./low_freq/house_1/channel_1.dat', 'r')
lines = entrada.read().splitlines()




# Since the methods use randomized initialization, let's fix a seed here
# to make this notebook reproducible


print("[OK] Treinamento inicializado...")
numpy.random.seed(42)
sample_period = 120
predictions = []
gts = []
fhmm = FHMM()
fhmm.train(top_5_train_elec[0], sample_period=sample_period)



def processa_dados(modelo, line):

    lista_pot = list()
    lista_index = list()
    print(len(line))
    for i in range(0,len(line),30):
        time_stamp, potencia = line[i].split()
        time_stamp = int(time_stamp)
        lista_pot.append(float(potencia))
        dt_object = datetime.fromtimestamp(time_stamp)
        lista_index.append(dt_object)
    
      
    df = pd.DataFrame({'power apparent':lista_pot},
                   index = lista_index)
    predicao = modelo.disaggregate_chunk(df)
    predicao.columns = ['Fridge', 'Light', 'Sockets', 'Microwave', 'Dish washer']
    list_geladeira = predicao['Fridge'].tolist()
    list_luzes = predicao['Light'].tolist()
    list_tomadas = predicao['Sockets'].tolist()
    list_microondas = predicao['Microwave'].tolist()
    list_lavadora = predicao['Dish washer'].tolist()

    for i in range(len(list_geladeira)):
        arquivo = open('geladeira.txt', 'w')
        arquivo.write(str(list_geladeira[i])+'\n')
        arquivo.close()
        arquivo = open('luzes.txt', 'w')
        arquivo.write(str(list_luzes[i])+'\n')
        arquivo.close()
        arquivo = open('tomadas.txt', 'w')
        arquivo.write(str(list_tomadas[i])+'\n')
        arquivo.close()
        arquivo = open('microondas.txt', 'w')
        arquivo.write(str(list_microondas[i])+'\n')
        arquivo.close()
        arquivo = open('lavadora.txt', 'w')
        arquivo.write(str(list_lavadora[i])+'\n')
        arquivo.close()
        time.sleep(i)
                   
print("[OK] Processo de desagregacao iniciado...")                    


for i in range(1539927, len(lines),60*30):
    aux = list()
    for j in range(0, 1800):
        aux.append(lines[i+j])
    thread_processamento = Thread(target=processa_dados,args=(fhmm, aux,))
    thread_processamento.start()
    time.sleep(60) #Espera 30 segundos
