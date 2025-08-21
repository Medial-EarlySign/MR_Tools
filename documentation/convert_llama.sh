#!/bin/bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

python /nas1/Work/python-env/python310/lib/python3.10/site-packages/transformers/models/llama/convert_llama_weights_to_hf.py --input_dir /nas1/Work/python-resources/common/llama/7B/llama-2-7b-chat --llama_version 2 --model_size 7B --output_dir /nas1/Work/python-resources/common/llama/7B/
#python ${0%/*}/transformers-main/src/transformers/models/llama/convert_llama_weights_to_hf.py  --input_dir /nas1/UsersData/Itamar/llama/llama-2-13b-chat --llama_version 2 --model_size 13B --output_dir /nas1/Work/python-resources/common/llama/13B/
   
   