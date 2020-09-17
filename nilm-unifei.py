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

from nilmtk.dataset_converters import convert_redd
convert_redd(r'low_freq', 'redd.h5')

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

# Since the methods use randomized initialization, let's fix a seed here
# to make this notebook reproducible
import numpy.random
numpy.random.seed(42)
sample_period = 120 
predictions = []
gts = []
fhmm = FHMM()
for building in range(5):
    print('*' * 20 )
    print('Casa : {}'.format(building))
    print('Usando o metodo FHHM...')
    print('*' * 20 )
    fhmm.train(top_5_train_elec[building], sample_period=sample_period)
    gt, prediction = predict(fhmm, test_elec[building], sample_period, train.metadata['timezone'])
    gts.append(gt)
    predictions.append(prediction)

for i in range(5):
    appliance_labels = [m.label() for m in gts[i].columns.values]
    gts[i].columns = appliance_labels
    predictions[i].columns = appliance_labels

list_geladeira = predictions[0]['Fridge'].tolist()
list_luzes = predictions[0]['Light'].tolist()
list_tomadas = predictions[0]['Sockets'].tolist()
list_microondas = predictions[0]['Microwave'].tolist()
list_lavadora = predictions[0]['Dish washer'].tolist()

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

    time.sleep(30)


    
