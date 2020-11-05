#!/bin/bash
mysql -u root -p -e "use nilmunifei;select * from geral_casa1;" > exports/geral_casa1.dat
mysql -u root -p -e "use nilmunifei;select * from geladeira_casa1;" > exports/geladeira_casa1.dat
mysql -u root -p -e "use nilmunifei;select * from cafeteira_casa1;" > exports/cafeteira_casa1.dat
mysql -u root -p -e "use nilmunifei;select * from geral_casa2;" > exports/geral_casa2.dat
mysql -u root -p -e "use nilmunifei;select * from geladeira_casa2;" > exports/geladeira_casa2.dat
mysql -u root -p -e "use nilmunifei;select * from maquina_casa2;" > exports/maquina_casa2.dat
mysql -u root -p -e "use nilmunifei;select * from geral_casa3;" > exports/geral_casa3.dat
mysql -u root -p -e "use nilmunifei;select * from geladeira_casa3;" > exports/geladeira_casa3.dat
mysql -u root -p -e "use nilmunifei;select * from chuveiro_casa3;" > exports/chuveiro_casa3.dat