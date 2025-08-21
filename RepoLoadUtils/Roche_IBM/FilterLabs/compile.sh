#!/bin/bash
MY_PATH=$(realpath ${0%/*})
g++ --std=c++11 -fopenmp -lpthread -Wall -march=native -ldl -Ofast -g ${MY_PATH}/main.cpp -o ${MY_PATH}/filter_app
