#!/bin/sh
#-------------------------------------------------------------------
# config.sh : Operator specifications for an ASGS instance
#-------------------------------------------------------------------
# Copyright(C) 2026 Jason Fleming
#
# This file is part of the ADCIRC Surge Guidance System (ASGS).
#
# The ASGS is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# ASGS is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# the ASGS.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------

# Fundamental

INSTANCENAME=%INSTANCENAME% # "name" of this ASGS process

# Input files and templates

GRIDNAME=LKOKE
parameterPackage=default   # <-----<<
createWind10mLayer="yes"   # <-----<<
source $SCRIPTDIR/config/mesh_defaults.sh

# Physical forcing (defaults set in config/forcing_defaults.sh)

TIDEFAC=off              # tide factor recalc
   HINDCASTLENGTH=0.0    # length of initial hindcast, from cold (days)
BACKGROUNDMET=off        # GFS download/forcing
   FORECASTCYCLE="06"
TROPICALCYCLONE=on       # tropical cyclone forcing
   VORTEXMODEL=SYMMETRIC
   STORM=%STORM%              # storm number, e.g. 05=ernesto in 2006
   YEAR=%YEAR%             # year of the storm
   RSSSITE=filesystem
   FTPSITE=$RSSSITE
   FDIR=$WORK
   HDIR=$WORK
WAVES=on                 # wave forcing
   REINITIALIZESWAN=no   # used to bounce the wave solution
VARFLUX=off              # variable river flux forcing
#
CYCLETIMELIMIT="99:00:00"

# Computational Resources (related defaults set in platforms.sh)

NCPU=15                # number of compute CPUs for all simulations
NCPUCAPACITY=9999
NUMWRITERS=0
#PPN=40
#JOBLAUNCHER='srun -n %totalcpu%'

# Post processing and publication

OPENDAPPOST=opendap_post2.sh
POSTPROCESS=POSTPROCESS=( vispipe_post.sh asgs_post.sh )

# Monitoring

enablePostStatus="no"
enableStatusNotify="no"
statusNotify="null"
EMAILNOTIFY="no"

# Initial state (overridden by STATEFILE after ASGS gets going)

COLDSTARTDATE=2017090812
HOTORCOLD=coldstart
LASTSUBDIR=null

#
# Scenario package
#
#PERCENT=default
SCENARIOPACKAGESIZE=3
case $si in
   -2)
       ENSTORM=hindcast
       ;;
   -1)
       # do nothing ... this is not a forecast
       ENSTORM=nowcast
       ;;
    0)
       ENSTORM=nhcTrack 
       ;;
    1)
       ENSTORM=veerRight100
       PERCENT=100
       ;;
    2)
       ENSTORM=veerLeft100
       PERCENT=-100
       ;;
    *)
       echo "CONFIGURATION ERROR: Unknown ensemble member number: '$si'."
      ;;
esac
#
PREPPEDARCHIVE=prepped_${GRIDNAME}_${INSTANCENAME}_${NCPU}.tar.gz
HINDCASTARCHIVE=prepped_${GRIDNAME}_hc_${INSTANCENAME}_${NCPU}.tar.gz
