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
import math
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
dicionario = list()
for line in lines:
    time_stamp, potencia = line.split()
    dicionario.append(time_stamp)
    dicionario.append(potencia)

def convert(lst): 
    res_dct = {lst[i]: lst[i + 1] for i in range(0, len(lst), 2)} 
    return res_dct

dicionario = convert(dicionario)

valor_referencia = open('./low_freq/house_1/channel_5.dat', 'r')
valor_geladeira = valor_referencia.read().splitlines()
dicionario_geladeira = list()
for line in valor_geladeira:
    time_stamp, potencia = line.split()
    dicionario_geladeira.append(time_stamp)
    dicionario_geladeira.append(potencia)

dicionario_geladeira = convert(dicionario_geladeira)

tempo = dicionario_geladeira.keys()

# Since the methods use randomized initialization, let's fix a seed here
# to make this notebook reproducible


print("[OK] Treinamento inicializado...")
numpy.random.seed(42)
sample_period = 120
predictions = []
gts = []
fhmm = FHMM()
fhmm.train(top_5_train_elec[0], sample_period=sample_period)

aux = list()
referencia = list()
erro = list()

def erro_quadratico(predicao, referencia):
    erro = 0.0
    for i in range(len(predicao)):
        erro += (predicao[i] - referencia[i])**2
    return math.sqrt(erro/len(predicao))

def processa_dados(modelo, line, referencia):
    global erro 
    start = datetime.now()
    lista_pot = list()
    lista_index = list()
    for i in range(0,len(line)):
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
    """list_luzes = predicao['Light'].tolist()
    list_tomadas = predicao['Sockets'].tolist()
    list_microondas = predicao['Microwave'].tolist()
    list_lavadora = predicao['Dish washer'].tolist()"""

    for i in range(len(list_geladeira)):
        arquivo = open('geladeira.txt', 'w')
        arquivo.write(str(list_geladeira[i])+'\n')
        arquivo.close()
        """arquivo = open('luzes.txt', 'w')
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
        arquivo.close()"""
    
    erro.append(erro_quadratico(list_geladeira, referencia))
    end = datetime.now()
    elapsed = end - start
    #print(elapsed.seconds,":",elapsed.microseconds) 
    

print("[OK] Processo de desagregacao iniciado...")                    

sample_variation = [1, 10, 100, 1000]
# Variar as amostras em cima do sistema e gerar graficos do valor dessas amostras 



for sample in sample_variation:

    samples = sample
    k = 0;
    erro = list()
    for amostra in tempo:
        try:
            aux.append(amostra + " " + dicionario[amostra])
            referencia.append(float(dicionario_geladeira[amostra]))
            samples -= 1
            if not samples:
                thread_processamento = Thread(target=processa_dados,args=(fhmm, aux, referencia))
                thread_processamento.start()
                aux = list()
                referencia = list()
                samples = sample
                k +=1; 
                if k == 1000:
                    break
                #time.sleep(30) #Espera 30 segundos
        except Exception as e :
            print("Uma inconsistencia de dado foi encontrada...")

    x = 0
    total = 0

    for e in erro:
        total += e
        x += 1

    total = total/x
    print("Media do erro quadratico: ", total)

    x=0
    lista = [x in range(len(erro)) ]
    plt.plot(erro)
    plt.show()
    