#!/bin/bash


x="iniciar"
menu ()
{
while true $x != "iniciar"
do
clear



echo "###################   Menu AWS  ##########################"
echo "#                                                        #"
echo "#  opção 1 Menu de Dados das Instancia da  AWS           #"
echo "#  opção 2 Menu de Inicialização Instancia AWS           #"
echo "#  opção 3 Sair do Menu                                  #"
echo "#                                                        #"
echo "##########################################################"

echo "Digite a opção desejada [1-3]:"
read x
echo "Opção informada ($x)"


case $x in 
	1)
	bash menuListarDataInstancia.sh
	;;
	2)
	bash menuIniciarInsta.sh
	;;
	3)
	echo "saindo..."
         sleep 1
         clear;
         exit;	
	;;
	*)
	echo "Opcao desconhecida"

esac

done

}
menu

