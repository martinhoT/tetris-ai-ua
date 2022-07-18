#!/bin/bash

PORT=8000
if [ -n $1 ]
then
    PORT=$1
fi

for i in {1..10}
do
    NAME="FMP" PORT=$PORT python3 ../student.py
    sleep 1
done


var=$(cat ../highscores.json | json_pp | grep "\s\+[0-9]\+" | sed 's/ *$//g')

scores=($var)

sum=0
for (( c=0; c<10; c++ ))
do
    echo Score $c : ${scores[c]}
    sum=$(($sum + ${scores[c]}))
done

echo $(($sum / 10)) > medias.txt
if [ $# -eq 1 ]
then
    echo --------------- NEW ARGUMENTS --------------- > medias.txt
fi
echo MÉDIA: $(($sum / 10))

rm ../highscores.json

eval "$(ps aux | awk '/server.py|viewer.py/ {printf "kill " $2 "\n"}')"
