#!/bin/bash
#export AM_CONFIG=$HOME/Documents/MES/AlgoMarkers/docker_images/LGI-Flag-ButWhy-3.1.2-Scorer/data/app/LGI-Flag-ButWhy-3.1.2-Scorer/LGI-ColonFlag-3.1.amconfig
export AM_CONFIG=$HOME/Documents/MES/AlgoMarkers/AM_LGI/AlgoMarker/ColonFlag_3.1.0.0/ColonFlag-3.1.amconfig
export AM_LIB=$HOME/Documents/MES/AlgoMarkers/AM_LGI/AlgoMarker/ColonFlag_3.1.0.0/libdyn_AlgoMarker.25102018_1.so
uvicorn server:app --reload --host 0.0.0.0 --port 8001