#!/usr/bin/env bash

python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

for d in ./*/
do
    if [ -f "$d/__main__.py" ]
    then
        echo "Running pulumi stack select in $d"
        # ls $d
        pulumi stack select dev -C $d
    fi
done
