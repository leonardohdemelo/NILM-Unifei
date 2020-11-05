"""Python file converter"""

files = ['geral_casa1' , 'geral_casa2', 'geral_casa3', 'geladeira_casa1', 'geladeira_casa2', 'geladeira_casa3', 'cafeteira_casa1', 'maquina_casa2', 'chuveiro_casa3'] 

for file in files:
    print("Formating file >>> " + file)
    f = open(file + '.dat', 'r')
    fw = open (file + 'formated.dat', 'w')
    start = True
    for line in f:
        if( not start):
            values = line.split('\t') 
            formated_string = values[1].split('.')[0] + " " + values[2]
            fw.write(formated_string)
        else:
            start = False
    f.close()
    fw.close()
    
print('Done formating')