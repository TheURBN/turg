#!/usr/bin/env bash
export TURGDB="mongodb://heroku_fczg4ktb:v0jevtt8ej0f3vr63ka13b0pmk@ds115625.mlab.com:15625/heroku_fczg4ktb"
python qbplotter.py --src samples/spotA.qb --x 510 --y 510 --turg-db ${TURGDB}
python qbplotter.py --src samples/spotB.qb --x 560 --y 540 --turg-db ${TURGDB}
python qbplotter.py --src samples/spotC.qb --x 675 --y 425 --turg-db ${TURGDB}
python qbplotter.py --src samples/spotD.qb --x 585 --y 405 --turg-db ${TURGDB}
python qbplotter.py --src samples/spotE.qb --x 480 --y 580 --turg-db ${TURGDB}