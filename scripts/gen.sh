#!/bin/bash

best_params=()

return_results() {
    echo "HOLES=${best_params[0]} MAX_HEIGHT=${best_params[1]} AVG_HEIGHT=${best_params[2]} HEIGHT_VARIANCE=${best_params[3]} CLEARED_LINES=${best_params[4]} CONTINUITY=${best_params[5]} CENTER_SCALE=${best_params[6]} HOLES_SCALE=${best_params[7]} CLEARED_LINES_SCALE=${best_params[8]}" > best.txt
    kill $(jobs -p)
    exit
}

trap return_results SIGINT
trap 'kill $(jobs -p)' EXIT

# Implementation of a genetic algorithm for hyperparameter optimization. Check http://www.scholarpedia.org/article/Genetic_algorithms and https://en.wikipedia.org/wiki/Genetic_algorithm.
# A "chromosome" is a string of 135 bits representing the four parameters.
# This chromosome, divided by 9, leaves 15 bits for each of the parameters (max value: 32767).

# Number of tetris games per generation is dependent on population size, N: N*G, G is the number of games made per individual.
population_size=$1
if [ -z $1 ]
then
    population_size="10"
fi

# Mutation chance is measured as $mutation_chance/32768.
# Default value is to always mutate, since the chromosomes are huge, and the mutation is very weak (only 1 bit change).
# Not only that, elitism is applied after mutation, so risk of losing the best parameters is null.
mutation_chance=$2
if [ -z $2 ]
then
    mutation_chance="32768"
fi

number_of_games=$3
if [ -z $3 ]
then
    number_of_games=10
fi

# Create 10 tetris servers, one for each of the 10 clients
for ((i=0; i<number_of_games; i++)); do python3 ../server.py --port 801$i > /dev/null 2>&1 & done

# Randomly generate various individuals (chromosomes)
population=()
for (( i=0; i<population_size; i++ ))
do
    bin0=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin0=$(echo ${bin0:$((${#bin0}-15)):15})
    bin1=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin1=$(echo ${bin1:$((${#bin1}-15)):15})
    bin2=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin2=$(echo ${bin2:$((${#bin2}-15)):15})
    bin3=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin3=$(echo ${bin3:$((${#bin3}-15)):15})
    bin4=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin4=$(echo ${bin4:$((${#bin4}-15)):15})
    bin5=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin5=$(echo ${bin5:$((${#bin5}-15)):15})
    bin6=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin6=$(echo ${bin6:$((${#bin6}-15)):15})
    bin7=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin7=$(echo ${bin7:$((${#bin7}-15)):15})
    bin8=000000000000000$(echo "obase=2;${RANDOM}" | bc)
    bin8=$(echo ${bin8:$((${#bin8}-15)):15})
    population+=("${bin0}${bin1}${bin2}${bin3}${bin4}${bin5}${bin6}${bin7}${bin8}")
done

# Can initialize with values from previous runs, or custom ones
if [[ -n $HOLES && -n $MAX_HEIGHT && -n $AVG_HEIGHT && -n $HEIGHT_VARIANCE && -n $CLEARED_LINES && -n $CONTINUITY && -n $CENTER_SCALE && -n $HOLES_SCALE && -n $CLEARED_LINES_SCALE ]]
then
    bin0=000000000000000$(echo "obase=2;${HOLES}" | bc)
    bin0=$(echo ${bin0:$((${#bin0}-15)):15})
    bin1=000000000000000$(echo "obase=2;${MAX_HEIGHT}" | bc)
    bin1=$(echo ${bin1:$((${#bin1}-15)):15})
    bin2=000000000000000$(echo "obase=2;${AVG_HEIGHT}" | bc)
    bin2=$(echo ${bin2:$((${#bin2}-15)):15})
    bin3=000000000000000$(echo "obase=2;${HEIGHT_VARIANCE}" | bc)
    bin3=$(echo ${bin3:$((${#bin3}-15)):15})
    bin4=000000000000000$(echo "obase=2;${CLEARED_LINES}" | bc)
    bin4=$(echo ${bin4:$((${#bin4}-15)):15})
    bin5=000000000000000$(echo "obase=2;${CONTINUITY}" | bc)
    bin5=$(echo ${bin5:$((${#bin5}-15)):15})
    bin6=000000000000000$(echo "obase=2;${CENTER_SCALE}" | bc)
    bin6=$(echo ${bin6:$((${#bin6}-15)):15})
    bin7=000000000000000$(echo "obase=2;${HOLES_SCALE}" | bc)
    bin7=$(echo ${bin7:$((${#bin7}-15)):15})
    bin8=000000000000000$(echo "obase=2;${CLEARED_LINES_SCALE}" | bc)
    bin8=$(echo ${bin8:$((${#bin8}-15)):15})
    population[0]="${bin0}${bin1}${bin2}${bin3}${bin4}${bin5}${bin6}${bin7}${bin8}"
fi

while true
do
    echo "New iteration!"

    # Fitness for each of the individuals, as an associative array
    declare -A fitness

    echo "Population:"
    printf "%s\n" "${population[@]}"
    for individual in "${population[@]}"
    do
        echo "Getting fitness of individual: $individual"

        # Extract each parameter from the individual
        params=()
        for param_idx in {0..8}
        do
            # Extract the respective 15 bit portion of the individual's chromosome
            # and convert the resulting number to base 10
            params+=( $( echo "obase=10;ibase=2;${individual:$((15*param_idx)):15}" | bc ) )
        done

        echo "Individual's parameters: ${params[@]}"

        # Store PIDs of the client processes, so that we can specifically wait for them afterwards
        pids=()

        # Calculate fitness, which is equal to the mean of 10 tetris games' scores.
        # This is done by $number_of_games clients and $number_of_games servers, so that it doesn't take forever.
        for ((i=0; i<number_of_games; i++))
        do
            PORT="801${i}" HOLES=${params[0]} MAX_HEIGHT=${params[1]} AVG_HEIGHT=${params[2]} HEIGHT_VARIANCE=${params[3]} CLEARED_LINES=${params[4]} CONTINUITY=${params[5]} CENTER_SCALE=${params[6]} HOLES_SCALE=${params[7]} CLEARED_LINES_SCALE=${params[8]} OUT="scores/score${i}.txt" python3 ../student.py > /dev/null 2>&1 &
            pids+=($!)
        done
        
        # Wait for the 10 games to finish.
        echo -n "Waiting for the games to finish..."
        for pid in "${pids[@]}"
        do
            wait $pid
        done
        echo " done!"

        sum=0
        for ((i=0; i<number_of_games; i++))
        do
            score=$(cat scores/score${i}.txt)
            sum=$((sum + score))
        done

        fitness[$individual]=$((sum / 10))
        echo "Fitness of this individual: ${fitness[$individual]}"
    done

    echo "Fitness obtained!"
    
    # Select best half of individuals according to fitness
    best_size=$((population_size/2))
    mapfile -t sorted_output < <(for individual in ${!fitness[@]}; do echo "$individual:${fitness[$individual]}"; done | sort -n -t: -k2 | tail -n ${best_size})
    sorted_individuals=($(printf "%s\n" ${sorted_output[@]} | cut -d: -f1))

    echo "Sorted individuals:"
    printf "%s\n" "${sorted_output[@]}"

    # Crossover
    # Each parent will create two children solutions.
    # 'step' is solely used for parent pair selection among the best half
    echo -n "Creating offspring"
    offspring=()
    step=$((best_size/2))
    for idx in "${!sorted_individuals[@]}"
    do
        parent1=${sorted_individuals[idx]}
        parent2=${sorted_individuals[$(( (idx+step)%best_size ))]}

        # Get a random separation point for the chromosomes
        delimiter=$(shuf -i 0-134 -n 1)

        offspring+=( "${parent1:0:$delimiter}${parent2:$delimiter:$((135-delimiter))}" )
        offspring+=( "${parent2:0:$delimiter}${parent1:$delimiter:$((135-delimiter))}" )
        echo -n ".."
    done
    echo " done!"

    # Mutation
    echo -n "Mutating"
    for idx in "${!offspring[@]}"
    do
        mutator="000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        if [ $RANDOM -lt $mutation_chance ]
        then
            mutated_bit=$(shuf -i 0-134 -n 1)
            mutator=$(echo "${mutator}" | sed "s/0/1/${mutated_bit}")
            if [ ${offspring[idx]:mutated_bit:1} -eq 1 ]
            then
                offspring[idx]=$(echo ${offspring[idx]} | sed "s/1/0/${mutated_bit}")
            else
                offspring[idx]=$(echo ${offspring[idx]} | sed "s/0/1/${mutated_bit}")
            fi
            echo -n "."
        fi
    done
    echo " done!"

    # Apply elitism: the best individual is kept for the next generation (guarantees that we always have the best solution found so far)
    offspring[0]=${sorted_individuals[-1]}
    echo "Best fitness: ${offspring[0]}"



    # Use new generation for next iteration
    population=(${offspring[@]})
    echo "Offspring created:"
    printf "%s\n" "${offspring[@]}"

    # Save params of best individual
    best_params_temp=()
    individual=${sorted_individuals[-1]}
    for param_idx in {0..8}
    do
        best_params_temp+=( $( echo "obase=10;ibase=2;${individual:$((15*param_idx)):15}" | bc ) )
    done
    
    best_params=(${best_params_temp[@]})
    echo "New best parameters saved"

    # Clear fitness
    unset fitness
done
