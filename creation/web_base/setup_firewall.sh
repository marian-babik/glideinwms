#!/bin/bash

#
# Project:
#   glideinWMS
#
# File Version:
#
# Description:
#   This script will setup the knobs that
#   are related to incoming connections/firewalls
#

glidein_config=$1
tmp_fname=${glidein_config}.$$.tmp

function warn {
 echo `date` $@ 1>&2
}

error_gen=`grep '^ERROR_GEN_PATH ' $glidein_config | awk '{print $2}'`

condor_vars_file=`grep -i "^CONDOR_VARS_FILE " $glidein_config | awk '{print $2}'`

# import add_config_line and add_condor_vars_line functions
add_config_line_source=`grep '^ADD_CONFIG_LINE_SOURCE ' $glidein_config | awk '{print $2}'`
source $add_config_line_source

##########################################################
# check if it should use CCB
##########################################################
out_ccb_str="False"
use_ccb=`grep '^USE_CCB ' $glidein_config | awk '{print $2}'`
if [ "$use_ccb" == "True" -o "$use_ccb" == "TRUE" -o "$use_ccb" == "T" -o "$use_ccb" == "Yes" -o "$use_ccb" == "Y" -o "$use_ccb" == "1" ]; then
    # ok, we need to define CCB variable

    collector_host=`grep '^GLIDEIN_Collector ' $glidein_config | awk '{print $2}'`
    if [ -z "$collector_host" ]; then
        #echo "No GLIDEIN_Collector found!" 1>&2
        STR="No GLIDEIN_Collector found!"
        "$error_gen" -error "setup_firewall.sh" "Corruption" "$STR" "attribute" "GLIDEIN_Collector"
        exit 1
    fi

    add_config_line CCB_ADDRESS $collector_host
    # and export it to Condor
    add_condor_vars_line CCB_ADDRESS C "-" "+" Y N "-"
    out_ccb_str="True"
fi


##########################################################
# check if it should use the shared_port_daemon
##########################################################
out_sharedp_str="False"
use_sharedp=`grep '^USE_SHARED_PORT ' $glidein_config | awk '{print $2}'`
if [ "$use_sharedp" == "True" -o "$use_sharedp" == "TRUE" -o "$use_sharedp" == "T" -o "$use_sharedp" == "Yes" -o "$use_sharedp" == "Y" -o "$use_sharedp" == "1" ]; then
    # ok, we need to enable the shared port
    daemon_list=`grep '^DAEMON_LIST ' $glidein_config | awk '{print $2}'`
    if [ -z "$daemon_list" ]; then
        # this is the default
        daemon_list="MASTER,STARTD"
    fi
    new_daemon_list="${daemon_list},SHARED_PORT"
    add_config_line DAEMON_LIST ${new_daemon_list}

    add_config_line USE_SHARED_PORT True
    out_sharedp_str="True"
fi


"$error_gen" -ok "setup_firewall.sh" "UseCCB" "${out_ccb_str}" "UseSharedPort" "${out_sharedp_str}"

exit 0
