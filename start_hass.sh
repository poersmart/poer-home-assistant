#!/bin/sh

mkdir -p ./config/custom_components/poer/
cp -af ./poer-home-assistant/custom_components/poer/  ./config/custom_components/ || exit 1

python -m homeassistant -c ./config
