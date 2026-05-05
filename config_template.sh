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

GRIDNAME=%GRIDNAME%        # <--<< jgf: I think this will always be LKOKE for this application
parameterPackage=default
createWind10mLayer="yes"
source $SCRIPTDIR/config/mesh_defaults.sh

# Physical forcing (defaults set in config/forcing_defaults.sh)

TIDEFAC=off              # tide factor recalc
   HINDCASTLENGTH=0.0    # length of initial hindcast, from cold (days)
BACKGROUNDMET=off        # GFS download/forcing
   FORECASTCYCLE="06"
TROPICALCYCLONE=on       # tropical cyclone forcing
   # VORTEXMODEL=SYMMETRIC # <--<< jgf: don't use this for real time operation, only for historical storms pre-2003
   STORM=%STORM%         # storm number, e.g. 05=ernesto in 2006
   YEAR=%YEAR%           # year of the storm
   HISTORICAL=%HISTORICAL%
   if [ $HISTORICAL -eq 1 ];then
      RSSSITE=filesystem   # <--<< jgf: only use this for testing or historical storms, not real time operation
      FTPSITE=$RSSSITE     # <--<< jgf: only use this for testing or historical storms, not real time operation
      FDIR=%FDIR%           # <--<< jgf: only use this for testing or historical storms, not real time operation
      HDIR=$FDIR           # <--<< jgf: only use this for testing or historical storms, not real time operation
   fi
WAVES=on                 # wave forcing
   REINITIALIZESWAN=no   # used to bounce the wave solution
VARFLUX=off              # variable river flux forcing
#
CYCLETIMELIMIT="99:00:00"

# Computational Resources (related defaults set in platforms.sh)

NCPU=%NCPU%                  # number of compute CPUs for all simulations
NCPUCAPACITY=%NCPUCAPACITY%  # <--<< jgf: set to a high number e.g., 9999 unless you want to limit the number of jobs the ASGS can submit at one time
NUMWRITERS=0
#PPN=40                           # <--<< jgf: should be removed, this is part of the platform specification
#JOBLAUNCHER='srun -n %totalcpu%' # <--<< jgf: should be removed, this is part of the platform specification

# Post processing and publication

OPENDAPPOST=opendap_post2.sh
POSTPROCESS=( vispipe_post.sh asgs_post.sh )  # # <--<< jgf: removed typo

# Monitoring

enablePostStatus="no"
enableStatusNotify="no"
statusNotify="null"
EMAILNOTIFY="no"

# Initial state (overridden by STATEFILE after ASGS gets going)

COLDSTARTDATE=%COLDSTARTDATE%
HOTORCOLD=%HOTORCOLD%           # <--<< jgf: for LKOKE this will be set to coldstart
LASTSUBDIR=null

nodal_attribute_default_values["sea_surface_height_above_geoid"]=%STARTING_WATER_LEVEL% # <--<< jgf: suggest changing to %STARTING_WATER_LEVEL% just to be descriptive

#
# Scenario package
#
#PERCENT=default
SCENARIOPACKAGESIZE=%NUM_FORECAST_SCENARIOS%  # <--<< jgf: I know you are not working on this yet; when you get to it, set to the number of forecast scenarios defined below
case $si in
   -1)
       # do nothing ... this is not a forecast
       ENSTORM=nowcast
       ;;
%STORM_SCENERIOS%
    *)
       echo "CONFIGURATION ERROR: Unknown ensemble member number: '$si'."
      ;;
esac
#
PREPPEDARCHIVE=prepped_${GRIDNAME}_${INSTANCENAME}_${NCPU}.tar.gz
HINDCASTARCHIVE=prepped_${GRIDNAME}_hc_${INSTANCENAME}_${NCPU}.tar.gz