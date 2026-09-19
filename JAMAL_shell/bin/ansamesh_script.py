#	**********************************************************************************************
#   * Program name      : ANSA
#   * Script            : ansamesh_script
#   *
#   * Author            : Maximiliano A. F. Souza
#   *
#   * Date created      : 20230301
#   *
#   * Purpose           : Mesh generation
#   *
#   * Revision History  :
#   *
#   * Date        Author                      Rev.   Changes made
#   * 20230301    Maximiliano A. F. Souza     .1     Released beta version
#   *
# **********************************************************************************************
#
#
import os
import shutil
from pathlib import Path
import platform
import sys
import os.path
import time
import math as mt
import fileinput
import re
import numpy as np
import mmap
import threading
import itertools
import ansa
import pprint
from ansa import *
from ansa.base import checks, Check
from ansa import calc
from itertools import islice
from collections import defaultdict
import subprocess
import json
from typing import Dict, Any
import logging

info = session.ApplicationInformation()
match = re.search(r"version:\s*([0-9]+\.[0-9]+\.[0-9]+)", info)
version = match.group(1)
if not version:
	raise RuntimeError("Could not determine ANSA version")
print("ANSA version:", version)
major = int(version.split('.')[0])
if major == 24:
	ansa.ImportCode(os.path.join(ansa.constants.app_root_dir, 'scripts', 'CFD', 'SetQualityCriteria.py'))
	from SetQualityCriteria import SetQualityCriteria_main as sq
elif major == 25:
	ansa.ImportCode(os.path.join(ansa.constants.app_root_dir, 'config', 'plugins', 'BuiltinScriptButtonsCFD', 'src', 'BuiltinScriptButtonsCFD.py'))
	import BuiltinScriptButtonsCFD_root
	from BuiltinScriptButtonsCFD_root import SetQualityCriteria
else:
    raise RuntimeError(f"Unsupported ANSA version: {version}")

#ansa.ImportCode(ansa.constants.app_root_dir+'scripts/CFD/SetQualityCriteria.py')
#from SetQualityCriteria import SetQualityCriteria_main
#This is for v24 and below
#ansa.ImportCode(os.path.join(ansa.constants.app_root_dir, 'scripts', 'CFD', 'SetQualityCriteria.py'))
#from SetQualityCriteria import SetQualityCriteria_main as sq
#This is for v25 and above
#ansa.ImportCode(os.path.join(ansa.constants.app_root_dir, 'config', 'plugins', 'BuiltinScriptButtonsCFD', 'src', 'BuiltinScriptButtonsCFD.py'))
#import BuiltinScriptButtonsCFD_root
#from BuiltinScriptButtonsCFD_root import SetQualityCriteria


class bcolors:
	# Starts color light blue
	HEADER = '\033[94m'
	# Starts color light green
	SUCCESS = '\033[92m'
	# Starts color light green
	GOOD_JOB = '\033[92m'
	# Starts color light green blinking
	GREAT_SUCCESS = '\033[92;5m'
	# Starts color yellow
	UP_TO_YOU = '\033[93m'
	# Starts color yellow
	WARNING = '\033[93m'
	# Starts color light red
	ERROR = '\033[91m'
	# Starts color red
	FAIL = '\033[31m'
	# Starts color red blinking
	MISERLY_FAIL = '\033[31;5m'
	# Ends color
	ENDC = '\033[0m'
	
# 	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$   MAIN   $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$


def yaml_to_json(yaml_file: str) -> Dict[str, Any]:
    """
    Converts a YAML file to a JSON dictionary using yq.

    Args:
        yaml_file: Path to the YAML file.

    Returns:
        A dictionary representing the JSON equivalent of the YAML.

    Raises:
        RuntimeError: If yq command fails or output is invalid JSON.
        FileNotFoundError: If the YAML file does not exist.
    """
    try:
        result = subprocess.run(
            ["yq", "-o=json", yaml_file], capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"yq command failed: {e.stderr}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON output from yq: {e}") from e
    except FileNotFoundError:
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")


def auto_config(yaml_file: str) -> None:
    """
    Loads YAML as JSON, maps to auto function parameters, and calls auto.

    Args:
        yaml_file: Path to the YAML file.

    Raises:
        ValueError: If required keys are missing or lengths exceed MAX_*.
        RuntimeError: From yaml_to_json.
    """
    data = yaml_to_json(yaml_file)

    # Validate and extract MAX_* constants
    max_geom_count = data.get("MAX_GEOM_COUNT")
    max_morph_params = data.get("MAX_MORPH_PARAMS")
    max_trans_params = data.get("MAX_TRANS_PARAMS")
    if max_geom_count is None:
        raise ValueError("Missing required key: MAX_GEOM_COUNT")
    if max_morph_params is None:
        raise ValueError("Missing required key: MAX_MORPH_PARAMS")
    if max_trans_params is None:
        raise ValueError("Missing required key: MAX_TRANS_PARAMS")

    # Basic validation for required keys and lengths
    required_keys = ["gdir", "geometry", "auto_trim_symm", "morph", "trans"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key: {key}")
    if len(data["geometry"]) > max_geom_count:
        raise ValueError(f"geometry list exceeds MAX_GEOM_COUNT ({max_geom_count})")
    if len(data["morph"]["params"]) > max_morph_params:
        raise ValueError(f"morph.params exceeds MAX_MORPH_PARAMS ({max_morph_params})")
    if len(data["trans"]["params"]) > max_trans_params:
        raise ValueError(f"trans.params exceeds MAX_TRANS_PARAMS ({max_trans_params})")

    # Map parameters
    params = {
        "geomdir": data["gdir"],
        "geom": data["geometry"][0] if len(data["geometry"]) > 0 else 0,
        "geom2": data["geometry"][1] if len(data["geometry"]) > 1 else '',
        "geom3": data["geometry"][2] if len(data["geometry"]) > 2 else '',
        "geom4": data["geometry"][3] if len(data["geometry"]) > 3 else '',
        "geom5": data["geometry"][4] if len(data["geometry"]) > 4 else '',
        "auto_trim_symm": int(data["auto_trim_symm"]),
        "basemeshdir": data["basemeshdir"],
        "basemesh": data["basemesh"],
        "bdir": data["bdir"],
        "bscn": data["bscn"],
        "sdir": data.get("sdir",os.path.dirname(os.path.abspath(__file__))),
        "scpt": data.get("scpt", os.path.basename(__file__)),
        "wrey": int(data["wrey"]),
        "wypls": float(data["wypls"]),
        "wlref": float(data["wlref"]),
        "wlay": float(data["wlay"]),
        "blref": float(data["blref"]),
        "msave": int(data["msave"]),
        "mtype": int(data["mtype"]),
        "scons": int(data["scons"]),
        "tcons": int(data["tcons"]),
        "bptch": float(data["bptch"]),
        "bnumb": int(data["bnumb"]),
        "propx0": float(data["propx0"]),
        "propy0": float(data["propy0"]),
        "propz0": float(data["propz0"]),
        "psaxis": data["psaxis"],
        "pptch": float(data["pptch"]),
        "ptoe": float(data["ptoe"]),
        "ftype": data["ftype"],
        "fcond": int(data["fcond"]),
        "fmout": int(data["fmout"]),
        "unout": int(data["unout"]),
        "scout": int(data["scout"]),
        "mirme": int(data["mirme"]),
        "zonen": data["zonen"],
        "zoneh": data["zoneh"],
        "zonel": data["zonel"],
        "morph_mode": int(data["morph"]["mode"]),
        "morph_param_01": int(data["morph"]["params"][0]) if len(data["morph"]["params"]) > 0 else 0,
        "morph_param_02": int(data["morph"]["params"][1]) if len(data["morph"]["params"]) > 1 else 0,
        "morph_param_03": int(data["morph"]["params"][2]) if len(data["morph"]["params"]) > 2 else 0,
        "morph_param_04": int(data["morph"]["params"][3]) if len(data["morph"]["params"]) > 3 else 0,
        "morph_param_05": int(data["morph"]["params"][4]) if len(data["morph"]["params"]) > 4 else 0,
        "morph_param_06": int(data["morph"]["params"][5]) if len(data["morph"]["params"]) > 5 else 0,
        "morph_param_07": int(data["morph"]["params"][6]) if len(data["morph"]["params"]) > 6 else 0,
        "morph_param_08": int(data["morph"]["params"][7]) if len(data["morph"]["params"]) > 7 else 0,
        "morph_param_09": int(data["morph"]["params"][8]) if len(data["morph"]["params"]) > 8 else 0,
        "morph_param_10": int(data["morph"]["params"][9]) if len(data["morph"]["params"]) > 9 else 0,
        "morph_param_11": int(data["morph"]["params"][10]) if len(data["morph"]["params"]) > 10 else 0,
        "morph_param_12": int(data["morph"]["params"][11]) if len(data["morph"]["params"]) > 11 else 0,
        "trans_mode": int(data["trans"]["mode"]),
        "trans_pids_a": data["trans"]["pids_a"],
        "trans_pids_b": data["trans"]["pids_b"],
        "trans_pids_c": data["trans"]["pids_c"],
        "trans_2point_a": data["trans"]["2point_a"],
        "trans_2point_b": data["trans"]["2point_b"],
        "trans_2point_c": data["trans"]["2point_c"],
        "trans_param_01": int(data["trans"]["params"][0]) if len(data["trans"]["params"]) > 0 else 0,
        "trans_param_02": int(data["trans"]["params"][1]) if len(data["trans"]["params"]) > 1 else 0,
        "trans_param_03": int(data["trans"]["params"][2]) if len(data["trans"]["params"]) > 2 else 0,
        "trans_param_04": int(data["trans"]["params"][3]) if len(data["trans"]["params"]) > 3 else 0,
        "trans_param_05": int(data["trans"]["params"][4]) if len(data["trans"]["params"]) > 4 else 0,
        "trans_param_06": int(data["trans"]["params"][5]) if len(data["trans"]["params"]) > 5 else 0,
        "trans_param_07": int(data["trans"]["params"][6]) if len(data["trans"]["params"]) > 6 else 0,
        "trans_param_08": int(data["trans"]["params"][7]) if len(data["trans"]["params"]) > 7 else 0,
        "trans_param_09": int(data["trans"]["params"][8]) if len(data["trans"]["params"]) > 8 else 0,
        "trans_param_10": int(data["trans"]["params"][9]) if len(data["trans"]["params"]) > 9 else 0,
        "trans_param_11": int(data["trans"]["params"][10]) if len(data["trans"]["params"]) > 10 else 0,
        "trans_param_12": int(data["trans"]["params"][11]) if len(data["trans"]["params"]) > 11 else 0,
        "sbox_max_len_surf": int(data["sbox_max_len_surf"]),
        "sbox_max_len_vol": int(data["sbox_max_len_vol"]),
        "surf_offset": float(data["surf_offset"]),
        "end_surf_offset": float(data["end_surf_offset"]),
        "sweep_distance": int(data["sweep_distance"]),
        "sfso_max_len_surf": int(data["sfso_max_len_surf"]),
        "sfso_max_len_vol": int(data["sfso_max_len_vol"]),
        "data": data,
    }
    #pprint.pprint(params)

    auto(**params)

    
def auto(geomdir, geom, geom2, geom3, geom4, geom5, auto_trim_symm, basemeshdir, basemesh, bdir, bscn, sdir, scpt, 
wrey, wypls, wlref, wlay, blref, msave, mtype, scons, tcons, bptch, bnumb, propx0, propy0, propz0, psaxis, pptch, ptoe, ftype, fcond, fmout, unout, scout, mirme, zonen, zoneh, zonel, 
morph_mode, morph_param_01, morph_param_02, morph_param_03, morph_param_04, morph_param_05, morph_param_06, morph_param_07, morph_param_08, morph_param_09, morph_param_10, morph_param_11, morph_param_12, 
trans_mode, trans_pids_a, trans_pids_b, trans_pids_c, trans_2point_a, trans_2point_b, trans_2point_c, trans_param_01, trans_param_02, trans_param_03, trans_param_04, trans_param_05, 
trans_param_06, trans_param_07, trans_param_08, trans_param_09, trans_param_10, trans_param_11, trans_param_12, sbox_max_len_surf, sbox_max_len_vol, surf_offset, end_surf_offset, sweep_distance, sfso_max_len_surf, sfso_max_len_vol,
data):
		
	global log_file
	global deck
	global gdir
	

	
	python_version=platform.python_version()
	print ('Python version: ' + python_version)
	
	#start = adir.find('ansa_v') + 6
	#end = adir.find('ansa64', start) -1
	#ansa_version = adir[start:end]
	#ansa_main_version = re.findall(r'\d+', ansa_version)[0]
	
	# Set Fluent deck
	base.SetCurrentDeck(constants.FLUENT)
	
	
	# ##################### MESH INPUT #####################
	# IS THIS A AIRFRAME MESH (1) OR A SLIDING MESH (2) ???
	mesh_type = mtype
	# ######################################################
	
	# ##################### MESH INPUT #####################
	# 		  *** THIS IS FOR SLIDING MESH ONLY ***
	# Blade pitch angle
	blade_pitch_angle = bptch
	# Number of blades
	num_blades = bnumb
	
	# Origin P0(x0,y0,z0) of the propeller coordinate system
	#x0 = 11641.2
	#y0 = -4480.0
	#z0 = 670.0
	x0 = propx0
	y0 = propy0
	z0 = propz0
	
	# Propeller pitch UP/DOWN angle	[deg]	(UP is positive, DOWN is negative)
	prop_pitch_angle = pptch
	# Propeller toe IN/OUT angle	[deg] 	LHS: (IN is negative, OUT is positive), RHS: (IN is positive, OUT is negative)
	prop_toe_angle = ptoe
	# ######################################################
	
	

#	Start log file
	log_file = 'meshlog'
	gdir = geomdir
	try:
		if os.path.isfile(os.path.join(gdir, log_file)):
			os.remove(os.path.join(gdir, log_file))
			
	except OSError as oserr:
		print('OS error during deleting file:')
		print(log_file)
		print('OS error: {0}'.format(oserr))	
		
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'#######################################  DIRECTORIES AND FILES  ############################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	message = 	'GEOMETRY DIRECTORY:\n'\
				+ str(os.path.abspath(gdir)) + '\n\n'\
				'GEOMETRY FILES:\n'\
				+ str(geom) + ' ' + str(geom2) + ' ' + str(geom3) + ' ' + str(geom4) + ' ' + str(geom5) + '\n\n'\
				'BATCH SCENARIOS DIRECTORY:\n'\
				+ str(os.path.abspath(bdir)) + '\n\n'\
				'BATCH SCENARIOS FILE:\n'\
				+ str(os.path.abspath(bscn)) + '\n\n'\
				'ANSAMESH SCRIPT DIRECTORY:\n'\
				+ str(os.path.abspath(sdir)) + '\n\n'\
				'ANSAMESH SCRIPT FILE:\n'\
				+ str(scpt) + '\n\n\n'
					
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'###############################  BOUNDARY LAYER MESH PARAMETERS CALCULATION  ###############################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	
	# Layers height factor to account for everything else different from the flat plate condition 
	# like pressure gradient influence on boundary layer height, etc.
	layerheight_factor = 1.4
	
	# Estimation of first layer height based on wing reference length for a turbulent boundary layer over a flat plate.
	wlay_y0 = first_layer_height(wrey, wlref, wypls)
	wlay_y0 = round(wlay_y0, 4)
	
	# Estimation of boundary layer height based on wing reference length for a turbulent boundary layer over a flat plate.
	wlay_h = total_layers_height(wrey, wlref)
	wlay_h = wlay_h*layerheight_factor
	
	# If wlay is a integer, calculate the layers growth ratio wlay_r for the wing set. 
	# Otherwise, calculate the number of layers wlay_n.	
	if isinstance(wlay, int):
		wlay_n = wlay - 1
		r0 = 1.1
		wlay_r = growth_factor_layers(wlay_y0, wlay_h, wlay_n)
		wlay_n = wlay_n + 1
	else:
		wlay_r = wlay
		wlay_n = number_of_layers(wlay_y0, wlay_h, wlay_r)
	
	# Estimation of boundary layer height of the fuselage based on the fuselage reference length. But the Reynolds number is based 
	# on the wing reference length.
	blay_h = total_layers_height(wrey, blref)
	blay_h = blay_h*layerheight_factor
	# Fuselage number of layers calculation based on wing first layer height and layers growth ratio.
	blay_n = number_of_layers(wlay_y0, blay_h, wlay_r)
	
	
	if ftype == "RANS":
		message =	'*********************************************************************************************  \n'\
					'Flow Type.........................................:' + str(ftype) 					 + '		\n'\
					'Reynolds Number...................................:' + str('{:<8.0f}'.format(wrey))  + '		\n'\
					'Wing Reference Length.............................:' + str('{:<4.4f}'.format(wlref)) + '	m	\n'\
					'Fuselage Reference Length.........................:' + str('{:<5.3f}'.format(blref)) + '	m	\n'\
					'Dimensionless Wall Distance Y+....................:' + str('{:<4.4f}'.format(wypls)) + '		\n'\
					'*********************************************************************************************  \n\n'\
					'*********************************************************************************************  \n'\
					'First Layer Height................................:' +  str('{:<4.4f}'.format(wlay_y0)) + '	mm		(everywhere)	\n'\
					'Boundary Layer Height.............................:' +  str('{:<7.1f}'.format(wlay_h))  + '	mm		(wing)			\n'\
					'Layers Growth Ratio...............................:' +  str('{:<4.4f}'.format(wlay_r))  + '			(everywhere)	\n'\
					'Number of Layers..................................:' +  str('{:<8.0f}'.format(wlay_n))  + '			(wing)			\n'\
					'Boundary Layer Height.............................:' +  str('{:<7.1f}'.format(blay_h))  + '	mm		(fuselage) 		\n'\
					'Number of Layers..................................:' +  str('{:<8.0f}'.format(blay_n))  + '			(fuselage)		\n'\
					'********************************************************************************************* \n\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	else:
		message =	'*********************************************************************************************  \n'\
					'Flow Type.........................................:' + str(ftype) 					 + '		\n'\
					'*********************************************************************************************  \n\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
	# Mark start time of the whole process
	t0 = time.time()

	
		
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'################################################  GEOMETRY  ################################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	# Variable deck will be OPENFOAM now
	deck = constants.OPENFOAM
	output_mesh_dir = ""
	# Check if geometry file exists
	if not os.path.isfile(os.path.join(gdir, geom)):
		upper_frame('e')
		message = '\nGeometry file ' + str(geom) + ' does not exist in directory. Abort! Abort!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('e')
		# Quit ANSA
		quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
	
	# Load file
	message = '\n\nLoading geometry ... '
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Open file 
	base.Open(os.path.join(gdir, geom))
	# Stop internal messages
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	message = 'Done loading geometry.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	# Get name of the geometry file
	full_path = base.DataBaseName() 
	#print('Full path to model file: ' + full_path)
	model_name = os.path.basename(full_path)
	name = os.path.splitext(model_name)[0]
	name = os.path.splitext(name)[0]
	#print(name)
    
	if geom2:
		# Check if geom2 file exists
		if not os.path.isfile(os.path.join(gdir, geom2)):
			upper_frame('e')
			message = '\nGeometry file ' + str(geom2) + ' does not exist in directory. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
		
		# Merge geom2 file
		message = '\n\nMerging geometry file ' + str(geom2)
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Merge geom2 file 
		utils.Merge(filename = os.path.join(gdir, geom2), property_offset = 'offset')
		# Stop internal messages
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
		message = 'Geometry file ' + str(geom2) + ' merged.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if "FARFIELD" not in geom2: 
			name = name + '_' + os.path.splitext(geom2)[0]
		
			
	if geom3:
		# Check if geom3 file exists
		if not os.path.isfile(os.path.join(gdir, geom3)):
			upper_frame('e')
			message = '\nGeometry file ' + str(geom3) + ' does not exist in directory. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
		
		# Merge geom3 file
		message = '\n\nMerging geometry file ' + str(geom3)
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Merge geom3 file 
		utils.Merge(filename = os.path.join(gdir, geom3), property_offset = 'offset')
		# Stop internal messages
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
		message = 'Geometry file ' + str(geom3) + ' merged.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if "FARFIELD" not in geom3: 
			name = name + '_' + os.path.splitext(geom3)[0]
		
	if geom4:
		# Check if geom4 file exists
		if not os.path.isfile(os.path.join(gdir, geom4)):
			upper_frame('e')
			message = '\nGeometry file ' + str(geom4) + ' does not exist in directory. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
		
		# Merge geom4 file
		message = '\n\nMerging geometry file ' + str(geom4)
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Merge geom4 file 
		utils.Merge(filename = os.path.join(gdir, geom4), property_offset = 'offset')
		# Stop internal messages
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
		message = 'Geometry file ' + str(geom4) + ' merged.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if "FARFIELD" not in geom4: 
			name = name + '_' + os.path.splitext(geom4)[0]
		
	if geom5:
		# Check if geom5 file exists
		if not os.path.isfile(os.path.join(gdir, geom5)):
			upper_frame('e')
			message = '\nGeometry file ' + str(geom5) + ' does not exist in directory. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
		
		# Merge geom5 file
		message = '\n\nMerging geometry file ' + str(geom5)
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Merge geom5 file 
		utils.Merge(filename = os.path.join(gdir, geom5), property_offset = 'offset')
		# Stop internal messages
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
		message = 'Geometry file ' + str(geom5) + ' merged.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if "FARFIELD" not in geom5: 
			name = name + '_' + os.path.splitext(geom5)[0]
		
	geom_pids = base.CollectEntities(constants.OPENFOAM, None, 'SHELL_PROPERTY')
	base.Not(geom_pids)
	
	
	base_mesh = False
	if basemeshdir and basemesh:
		# Check if basemesh exists
		if not os.path.isfile(os.path.join(basemeshdir, basemesh)):
			upper_frame('e')
			message = '\nBasemesh does not exist in directory. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
		if os.path.isdir(basemeshdir):
			if os.path.isfile(os.path.join(basemeshdir, basemesh)):
				message = '\n\nMerging base mesh ...'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				utils.Merge(filename = os.path.join(basemeshdir, basemesh), property_offset = 'offset')
				# Stop internal messages
				m.stop_buffering()
				ret_buffer = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
				message = 'Base mesh merged.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				base_mesh = True
				base_vols = base.CollectEntities(deck, None, 'VOLUME')
				if base_vols:
					base.Or(base_vols)
				base.FacesFreezeUnFreeze(faces='visible')
	base.All()
	
	# Check if batch mesh scenario exists
	if not os.path.isfile(os.path.join(bdir, bscn)):
		upper_frame('e')
		message = '\nBatch mesh scenarios does not exist in directory. Abort! Abort!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('e')
		# Quit ANSA
		quit_ansa(gdir, output_mesh_dir, log_file, log_file, 2)
		
	# Merge in the ANSA file with the predefined Batch Mesh Scenarios
	message = '\n\nMerging batch mesh scenarios ...'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Merge batch scenarios files 
	utils.Merge(filename = os.path.join(bdir, bscn), property_offset = 'offset')
	# Stop internal messages
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	message = 'Batch mesh scenarios merged.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	#full_path = base.DataBaseName() 
	#print('Full path to model file: ' + full_path)
	#model_name = os.path.basename(full_path)
	#name = os.path.splitext(model_name)[0]
	#name = os.path.splitext(name)[0]
	#print(name)
	
	
	# Freeze all surfaces meshed with 4SIDED 
	deck = constants.OPENFOAM
	faces = base.CollectEntities(deck, None, 'FACE')
	faces_with_map = []
	foundmap = 0
	for face in faces:
		ret = base.GetEntityCardValues(deck, face, ['Meshed With'])
		if ret['Meshed With'] == '4 SIDED':
			faces_with_map.append(face)
			foundmap = 1
	if foundmap == 1:
		print ("ok")
		base.Or(faces_with_map) 
		base.FacesFreezeUnFreeze(faces='visible')
	base.All()
	
	#################################### TRANSFORM OPERATIONS ##########################
	if trans_mode == 1:
		name = name + '_t' 
		
		trans_params = [trans_param_01, trans_param_02, trans_param_03, trans_param_04, trans_param_05, trans_param_06, trans_param_07, trans_param_08, trans_param_09, trans_param_10, trans_param_11, trans_param_12]
		# 1. Find index of last non‑zero (or -1 if all zero)
		last = max((i for i, v in enumerate(trans_params) if v != 0), default=-1)
		# 2. Build filename
		if last == -1:
			name = name           # no non-zero values
		else:
			parts = trans_params[: last + 1]  # include leading zeros up to last non-zero
			name = name + "_" + "_".join(str(v) for v in parts)
			
		message = '\n\n\n\n'\
		'############################################################################################################\n'\
		'#############################################  TRANSFORM MESH  #############################################\n'\
		'############################################################################################################\n'\
		'\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'h')
		
		# LEX **********************************************************************
		trans_pids = []
		trans_pids_names = trans_pids_a.split()
		deck = constants.OPENFOAM
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		morph_boxes = base.CollectEntities(deck, None, "MORPHBOX")
		for pid in pids:
			if pid._name in trans_pids_names:
				trans_pids.append(pid)
		for morph_box in morph_boxes:
			if morph_box._name == 'strake_bend':
				trans_pids.append(morph_box)
		points = [float(x) for x in trans_2point_a.split()]
		
		if trans_param_01 != 0:
			x0=points[0]
			y0=points[1]
			z0=points[2]
			scale_factor=trans_param_01
			base.GeoScale('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, scale_factor, trans_pids)
			message = '\nScaling PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nScale factor = ' + str(scale_factor) + '\nOrigin Scaling Point [mm] = ' + str(x0) + ', ' + str(y0) + ', ' + str(z0)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if trans_param_02 != 0:
			x0=points[0]
			y0=points[1]
			z0=points[2]
			x1=points[3]
			y1=points[4]
			z1=points[5]
			rotate_angle=trans_param_02
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, x1, y1, z1, rotate_angle, trans_pids)
			message = '\nRotating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nRotage angle [deg] = ' + str(rotate_angle) + '\nHinge Points [mm] = (' + str(x0) + ', ' + str(y0) + ', ' + str(z0) + ')  (' + str(x1) + ', ' + str(y1) + ', ' + str(z1) + ')'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if trans_param_03 != 0:
			dx=trans_param_03
			dy=0
			dz=0
			base.GeoTranslate('MOVE', 0, 'SAME PART', 'NONE', dx, dy, dz, trans_pids)
			message = '\nTranslating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nTranslate X [mm] = ' + str(dx)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
		if trans_param_04 != 0:
			dx=0
			dy=0
			dz=trans_param_04
			base.GeoTranslate('MOVE', 0, 'SAME PART', 'NONE', dx, dy, dz, trans_pids)
			message = '\nTranslating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nTranslate Z [mm] = ' + str(dz)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
		# Tail	**********************************************************************
		trans_pids.clear()
		trans_pids_names = trans_pids_b.split()
		deck = constants.OPENFOAM
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		for pid in pids:
			if pid._name in trans_pids_names:
				trans_pids.append(pid)
		points = []
		points = [float(x) for x in trans_2point_b.split()]
		
		if trans_param_05 != 0:
			x0=points[0]
			y0=points[1]
			z0=points[2]
			scale_factor=trans_param_05
			base.GeoScale('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, scale_factor, trans_pids)
			message = '\nScaling PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nScale factor = ' + str(scale_factor) + '\nOrigin Scaling Point [mm] = ' + str(x0) + ', ' + str(y0) + ', ' + str(z0)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')	
		
		if trans_param_06 != 0:
			x0=points[0]
			y0=points[1]
			z0=points[2]
			x1=points[3]
			y1=points[4]
			z1=points[5]
			rotate_angle=trans_param_06
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, x1, y1, z1, rotate_angle, trans_pids)
			message = '\nRotating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nRotage angle [deg] = ' + str(rotate_angle) + '\nHinge Points [mm] = (' + str(x0) + ', ' + str(y0) + ', ' + str(z0) + ')  (' + str(x1) + ', ' + str(y1) + ', ' + str(z1) + ')'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if trans_param_07 != 0:
			dx=trans_param_07
			dy=0
			dz=0
			base.GeoTranslate('MOVE', 0, 'SAME PART', 'NONE', dx, dy, dz, trans_pids)
			message = '\nTranslating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nTranslate X [mm] = ' + str(dx)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
		if trans_param_08 != 0:
			dx=0
			dy=0
			dz=trans_param_08
			base.GeoTranslate('MOVE', 0, 'SAME PART', 'NONE', dx, dy, dz, trans_pids)
			message = '\nTranslating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nTranslate Z [mm] = ' + str(dz)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		# Flap **********************************************************************
		trans_pids.clear()
		trans_pids_names = trans_pids_c.split()
		deck = constants.OPENFOAM
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		for pid in pids:
			if pid._name in trans_pids_names:
				trans_pids.append(pid)
		points = []
		points = [float(x) for x in trans_2point_c.split()]
		
		if trans_param_09 != 0:
			x0=points[0]
			y0=points[1]
			z0=points[2]
			x1=points[3]
			y1=points[4]
			z1=points[5]
			rotate_angle=trans_param_09
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, x1, y1, z1, rotate_angle, trans_pids)
			message = '\nRotating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nRotage angle [deg] = ' + str(rotate_angle) + '\nHinge Points [mm] = (' + str(x0) + ', ' + str(y0) + ', ' + str(z0) + ')  (' + str(x1) + ', ' + str(y1) + ', ' + str(z1) + ')'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if trans_param_10 != 0:
			x2=points[0]
			y2=points[1]
			z2=points[2]
			x3=points[0]+100
			y3=points[1]
			z3=points[2]
			rotate_angle=trans_param_10
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x2, y2, z2, x3, y3, z3, rotate_angle, trans_pids)
			message = '\nRotating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nRotage angle [deg] = ' + str(rotate_angle) + '\nHinge Points [mm] = (' + str(x0) + ', ' + str(y0) + ', ' + str(z0) + ')  (' + str(x1) + ', ' + str(y1) + ', ' + str(z1) + ')'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if trans_param_11 != 0:
			dx=trans_param_11
			dy=0
			dz=0
			base.GeoTranslate('MOVE', 0, 'SAME PART', 'NONE', dx, dy, dz, trans_pids)
			message = '\nTranslating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nTranslate X [mm] = ' + str(dx)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if trans_param_12 != 0:
			dx=0
			dy=0
			dz=trans_param_12
			base.GeoTranslate('MOVE', 0, 'SAME PART', 'NONE', dx, dy, dz, trans_pids)
			message = '\nTranslating PIDs ' + ' '.join(map(str, trans_pids_names)) + '\nTranslate Z [mm] = ' + str(dz)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')

	##############################################################################################################
	
	# **************************************************************************************************************
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'###########################################  CREATING SIZE FIELD  ##########################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	# Create size field SIZE BOX
	if sbox_max_len_surf != 0 and sbox_max_len_vol != 0:
		deck = constants.OPENFOAM
		size_boxes = base.CollectEntities(deck, None, 'SIZE_BOX')
		for size_box in size_boxes:
			sf = base.CreateEntity(constants.NASTRAN, "SIZE FIELD")
			sbox = mesh.GetNewSizeFieldSizeBoxRule(size_field=sf, name="size_box", max_surf_len=sbox_max_len_surf, max_vol_len=sbox_max_len_vol)
			mesh.AddContentsToSizeFieldRule(entities=size_box, rule=sbox)
			
			
		
		
	# Create size field SURFACE OFFSET
	if sfso_max_len_surf != 0 and sfso_max_len_vol != 0 and surf_offset != 0:
		
		message =	'maximum_surface_length = ' +  str('{:<4.1f}'.format(sfso_max_len_surf))  + ' mm\n'\
		'maximum_volume_length = ' +  str('{:<4.1f}'.format(sfso_max_len_vol))  + ' mm\n'\
		'sweep_distance = ' +  str('{:<4.1f}'.format(sweep_distance))  + ' mm\n'\
		'surf_offset = ' +  str('{:<4.1f}'.format(surf_offset))  + ' mm\n'\
		'end_surf_offset = ' +  str('{:<4.1f}'.format(end_surf_offset))  + ' mm\n\n'
		
		if sweep_distance == 0:
			variable_shape = "false"
		else:
			variable_shape = "true"
			if end_surf_offset == 0:
				upper_frame('e')
				message = '\n Since sweep_distance is different then zero, end_surf_offset must be different than zero too.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				lower_frame('e')
				# Quit ANSA
				quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
		
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		deck = constants.OPENFOAM
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		surf_offset_pids = []
		for pid in pids:
			if pid._name != 'BDRY_SYM' and pid._name != 'BDRY_FAR':
				surf_offset_pids.append(pid)
		sf = base.CreateEntity(constants.NASTRAN, "SIZE FIELD")
		surf_off = mesh.GetNewSizeFieldSurfaceOffsetRule(size_field=sf,name="surface_offset",max_surf_len=sfso_max_len_surf,max_vol_len=sfso_max_len_vol,offset=1000,)
		mesh.AddContentsToSizeFieldRule(entities=surf_offset_pids, rule=surf_off)
		sf_rules = mesh.GetRulesFromSizeField(sf)
		size_field_param_input = os.path.join(bdir, 'SizeFieldSurfaceOffsetRule_params.ansa_mpar')
		size_field_param_output = os.path.join(bdir, 'params.ansa_mpar')
		if os.path.isfile(size_field_param_input):
			with open(size_field_param_input, 'r') as fin, open(size_field_param_output, 'w') as fout:
				for line in fin:
					new_line = (
						line
						.replace("%sfso_max_len_surf%", str(sfso_max_len_surf))
						.replace("%sfso_max_len_vol%",  str(sfso_max_len_vol))
						.replace("%sweep_distance%",  str(sweep_distance))
						.replace("%variable_shape%",  str(variable_shape))
						.replace("%surf_offset%",  str('{:<4.1f}'.format(surf_offset)))
						.replace("%end_surf_offset%",  str(end_surf_offset))
					)
					fout.write(new_line)
			mesh.ReadSizeFieldRuleParams(rule=sf_rules[0], mpar_file=size_field_param_output)
	
	
	# Build all size fields
	size_fields = base.CollectEntities(deck, None, 'SIZE FIELD')
	for size_field in size_fields:
		mesh.ApplySizeFieldFilters(size_field)
		mesh.BuildSizeField(size_field)
		
	# **************************************************************************************************************
	
    # Auto trim on symmetry plane
	if auto_trim_symm == 1:
		message = '\n\nPerforming auto trim of the symmetry plane ...'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		auto_trim_on_symmetry_plane()
    
    
	blade_mesh = False
	disk_mesh = False
	spinner_mesh = False
	pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
	for pid in pids:
		if pid._name.startswith('X_UPP'):
			blade_mesh = True
		if pid._name.startswith('X_DSK'):
			disk_mesh = True
		if pid._name.startswith('X.SPN'):
			spinner_mesh = True



	# Sliding mesh autro-trim and pitch-toe process
	if mesh_type == 2 and blade_mesh:
		message = '\n\nStarting sliding mesh autro-trim and pitch-toe process.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		name = name + '_Blades_' + str(num_blades) + '_BladesPitch_' + str('{:<3.2f}'.format(blade_pitch_angle)) + '_PropPitchToe_' + str('{:<3.2f}'.format(prop_pitch_angle)) + '_' + str('{:<3.2f}'.format(prop_toe_angle))
		message = '\nNew file name: ' + name
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		bad_chars = ['.', ';', ':', '!', '*']
		for i in bad_chars: 
			name = name.replace(i, '')
		
		coord_systems = base.CollectEntities(deck, None, 'CORD_R')
		prop_axis = False
		for coord_system in coord_systems:
			if coord_system._name == 'Propeller_Axis':
				prop_current_coord_system = coord_system
				prop_axis = True
		if not prop_axis:
			upper_frame('e')
			message = '\nPropeller coordinate system named Propeller_Axis of type CORD_R not found. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
			
		
		# Propeller current coordinate system: xaxis, yaxis, zaxis
		xaxis = calc.GetCoordTransformMatrix4x3(deck, prop_current_coord_system, 0, 0, 0)[0]
		yaxis = calc.GetCoordTransformMatrix4x3(deck, prop_current_coord_system, 0, 0, 0)[1]
		zaxis = calc.GetCoordTransformMatrix4x3(deck, prop_current_coord_system, 0, 0, 0)[2]
		
		# Calculate the rotation matrix given propeller pitch and toe angles
		thetax = mt.radians(0)
		thetay = mt.radians(prop_pitch_angle)
		thetaz = mt.radians(prop_toe_angle)
		rot_mat = rotation_matrix(thetax, thetay, thetaz)
		
		# Propeller new coordinate system: e1, e2, e3
		e1 = rot_mat.dot(xaxis)
		e2 = rot_mat.dot(yaxis)
		e3 = rot_mat.dot(zaxis)
		# Components of the unit vector e1 (propeller drive shaft axis)
		e1x = e1[0]
		e1y = e1[1]
		e1z = e1[2]
		# Components of the unit vector e2
		e2x = e2[0]
		e2y = e2[1]
		e2z = e2[2]
		# Components of the unit vector e3
		e3x = e3[0]
		e3y = e3[1]
		e3z = e3[2]
		
		# Point P1(x1,y1,z1) along the xaxis vector from the origin point P0
		x1 = x0 + xaxis[0]
		y1 = y0 + xaxis[1]
		z1 = z0 + xaxis[2]
		# Point P2(x2,y2,z2) along the yaxis vector from the origin point P0
		x2 = x0 + yaxis[0]
		y2 = y0 + yaxis[1]
		z2 = z0 + yaxis[2]
		# Point P3(x3,y3,z3) along the zaxis vector from the origin point P0
		x3 = x0 + zaxis[0]
		y3 = y0 + zaxis[1]
		z3 = z0 + zaxis[2]
		# Point P4(x4,y4,z4) along the e1 vector from the origin point P0
		x4 = x0 + e1x
		y4 = y0 + e1y
		z4 = z0 + e1z
		# Point P5(x5,y5,z5) along the e2 vector from the origin point P0
		x5 = x0 + e2x
		y5 = y0 + e2y
		z5 = z0 + e2z
		# Point P6(x6,y6,z6) along the e3 vector from the origin point P0
		x6 = x0 + e3x
		y6 = y0 + e3y
		z6 = z0 + e3z
		
		message =	'\n*********************************************************************************************  \n'\
					'                                PROPELLER PITCH AND TOE ANGLES                                     \n'\
					'Propeller pitch angle [deg].......................: ' + str('{:<3.2f}'.format(prop_pitch_angle))  + '\n'\
					'Propeller toe angle [deg].........................: ' + str('{:<3.2f}'.format(prop_toe_angle))  + '\n\n'\
					'                             PROPELLER COORDINATE SYSTEM: e1, e2, e3                           \n'\
					'Components of the unit vector e1                                                               \n'\
					'e1x...............................................: ' + str('{:<8.10f}'.format(e1x))  + '		\n'\
					'e1y...............................................: ' + str('{:<8.10f}'.format(e1y))  + '		\n'\
					'e1z...............................................: ' + str('{:<8.10f}'.format(e1z))  + '		\n'\
					'Components of the unit vector e2                                                               \n'\
					'e2x...............................................: ' + str('{:<8.10f}'.format(e2x))  + '		\n'\
					'e2y...............................................: ' + str('{:<8.10f}'.format(e2y))  + '		\n'\
					'e2z...............................................: ' + str('{:<8.10f}'.format(e2z))  + '		\n'\
					'Components of the unit vector e3                                                               \n'\
					'e3x...............................................: ' + str('{:<8.10f}'.format(e3x))  + '		\n'\
					'e3y...............................................: ' + str('{:<8.10f}'.format(e3y))  + '		\n'\
					'e3z...............................................: ' + str('{:<8.10f}'.format(e3z))  + '		\n\n'\
					'                     ORIGEM OF THE PROPELLER COORDINATE SYSTEM: P0(x0,y0,z0)                   \n'\
					'x0 [mm]...........................................: ' + str('{:<8.3f}'.format(x0))  + '		\n'\
					'y0 [mm]...........................................: ' + str('{:<8.3f}'.format(y0))  + '		\n'\
					'z0 [mm]...........................................: ' + str('{:<8.3f}'.format(z0))  + '		\n'\
					'*********************************************************************************************  \n'
		pitch_toe_filename = 'PropPitchToeLHS_' + str('{:<3.2f}'.format(prop_pitch_angle)) + '_' + str('{:<3.2f}'.format(prop_toe_angle))
		for i in bad_chars: 
			pitch_toe_filename = pitch_toe_filename.replace(i, '')
		print_message(os.path.join(gdir, pitch_toe_filename), message, 0, 'b')
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		blade_side = False
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		for pid in pids:
			if pid._name.endswith('-LH'):
				blade_side = '-LH'
			if pid._name.endswith('-RH'):
				blade_side = '-RH'
		if not blade_side:
			upper_frame('w')
			message = '\nModel side -LH or -RH not found!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('w')

				
		step_angle = 360/num_blades
		propeller_pid_names = ['X_UPP', 'X_LOW', 'X_TED', 'X_CAP', 'X_ITF']
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		propeller_pids = []
		for pid in pids:
			if any(i in pid._name for i in propeller_pid_names):
				propeller_pids.append(pid)
				
		working_planes = base.CollectEntities(deck, None, 'WPLANE')
		blade_plane = False
		for working_plane in working_planes:
			if working_plane._name == 'Plane_Blade_Rc07':
				propeller_pids.append(working_plane)
				blade_plane = True
		if not blade_plane:
			upper_frame('w')
			message = '\nBlade working plane (Plane_Blade_Rc07) not found!\nIt is used to print the blade pitch measurement value only.\nIt does not affect the process.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('w')
			
		# Blade pitch angle
		if psaxis.strip() == 'e1':
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, x3, y3, z3, blade_pitch_angle, propeller_pids)
		elif psaxis.strip() == 'e2':
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, x3, y3, z3, blade_pitch_angle, propeller_pids)
		elif psaxis.strip() == 'e3':
			base.GeoRotate('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, x1, y1, z1, blade_pitch_angle, propeller_pids)
		else:
			upper_frame('e')
			message = '\nThe psaxis value is not valid. Enter e1, e2 or e3 only. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
		
		measurement = base.GetEntity(deck, 'MEASUREMENT', 1)
		if measurement:
			measured_angle = measurement.get_entity_values(deck, ['RESULT'])['RESULT']
			message = '\nBlade Pitch Angle: ' + str('{:<4.6f}'.format(measured_angle))
			print_message(os.path.join(gdir, pitch_toe_filename), message, 1, 'b')
		
		# Rotate blades around the propeller shaft axis
		message = '\n\nNumber of Blades: ' + str(num_blades) + '\n\nBlades will be created by rotating blade #1 around the propeller shaft axis.\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		faces_to_copy = base.CollectEntities(deck, propeller_pids, 'FACE')
		for i in range(num_blades - 1):
			message = '\nCreating blade # ' +  str(i+2)
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			pid_collector = base.CollectNewModelEntities(deck, 'SHELL_PROPERTY')
			if psaxis.strip() == 'e1':
				base.GeoRotate('COPY', 'AUTO_OFFSET', 'SAME PART', 'NONE', x1, y1, z1, x0, y0, z0, step_angle * (i+1), faces_to_copy)	
			elif psaxis.strip() == 'e2':
				base.GeoRotate('COPY', 'AUTO_OFFSET', 'SAME PART', 'NONE', x2, y2, z2, x0, y0, z0, step_angle * (i+1), faces_to_copy)
			elif psaxis.strip() == 'e3':
				base.GeoRotate('COPY', 'AUTO_OFFSET', 'SAME PART', 'NONE', x3, y3, z3, x0, y0, z0, step_angle * (i+1), faces_to_copy)
			else:
				upper_frame('e')
				message = '\nThe psaxis value is not valid. Enter e1, e2 or e3 only. Abort! Abort!'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				lower_frame('e')
				# Quit ANSA
				quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
				
			new_pids = pid_collector.report()
			del pid_collector		
			for new_pid in new_pids:
				new_name = new_pid._name[:-6] + '-0' + str(i+2) + blade_side
				message = '\nNew name: ' + new_name + '   id: ' + str(new_pid._id)
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				new_pid.set_entity_values(deck, {'Name':new_name})
				
		t1 = time.time()
		message = '\n\nTime...........................:' + str('{:5.2f}'.format((t1 - t0)/60)) + ' minutes'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		if spinner_mesh:
			message = '\n\nInitiating auto-trim function...'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			_autotrim()
			message = '\nAuto-trim complete.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
			
		propeller_pid_names = ['X_UPP', 'X_LOW', 'X_TED', 'X_CAP', 'X_ITF', 'X_BOX', 'X.SPN']
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		propeller_pids = []
		for pid in pids:
			if any(i in pid._name for i in propeller_pid_names):
				propeller_pids.append(pid)
				
		working_planes = base.CollectEntities(deck, None, 'WPLANE')
		prop_planes = False
		for working_plane in working_planes:
			if working_plane._name == 'Plane_e1e3' or working_plane._name == 'Plane_e1e2' or working_plane._name == 'Plane_e2e3' or working_plane._name == 'Plane_Blade_Rc07':
				propeller_pids.append(working_plane)
				prop_planes = True
		if not prop_planes:
			upper_frame('w')
			message = '\nPropeller working planes (Plane_e1e3, Plane_e1e2, Plane_e2e3, Plane_Blade_Rc07) not found!\nIt is used to print the measurement of the pitch/toe and blade pitch angles only.\nIt does not affect the process.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('w')
			
		coord_systems = base.CollectEntities(deck, None, 'CORD_R')
		for coord_system in coord_systems:
			if coord_system._name == 'AxisSystem.2':
				propeller_pids.append(coord_system)
				
		coord_systems = base.CollectEntities(deck, None, 'CORD_NODES_R')
		for coord_system in coord_systems:
			propeller_pids.append(coord_system)
		
		# Apply Pitch and Toe angles
		base.GeoTransform('MOVE', 0, 'SAME PART', 'NONE', x0, y0, z0, xaxis[0], xaxis[1], xaxis[2], yaxis[0], yaxis[1], yaxis[2], x0, y0, z0, e1x, e1y, e1z, e2x, e2y, e2z, propeller_pids)
		message = '\n\nPitch-Toe angles applyed.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		t2 = time.time()
		message = '\n\nTime...........................:' + str('{:5.2f}'.format((t2 - t1)/60)) + ' minutes'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	if mesh_type == 1 and disk_mesh:
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		for pid in pids:
			if pid._name.startswith('X_BOX'):
				base.SetEntityCardValues(deck, pid, {'USE_IN_MODEL':'NO'})
				#vals = base.GetEntityCardValues(deck, pid, ['USE_IN_MODEL'])
				#print(vals['USE_IN_MODEL'])
				message = '\nPID ' + pid._name + ' will not be used in model.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
	for pid in pids:
		if pid._name.startswith('X_BOX-02-LH'):
			# Saving only the propeller box to be used in mesh group 1, the airframe group
			message = '\n\nSaving file with the propeller box only...\n'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
			# Rename box
			pid.set_entity_values(deck, {'Name':'X_BOX-01-LH'})
			base.Or(pid)
			# Get internal messages
			m = utils.Messenger()
			m.start_buffering()
			# Reorient
			base.Orient()
			# Save visible as
			base.SaveVisibleAs(ansa.ScriptCurrentDir() + name + '__PropellerBox.ansa')
			# Reorient
			base.Orient()
			m.stop_buffering()
			ret_buffer = m.get_buffer()
			# Write internal messages to log file
			for i in ret_buffer:
				message = i + '\n'
				print_message(os.path.join(gdir, log_file), message, 0, 'b')
			m.clear()
			# restore name 
			pid.set_entity_values(deck, {'Name':'X_BOX-02-LH'})

	# Bring everything to visible
	base.All()
	

	if not 'SURF_MESH' in geom and not 'LAYERS_MESH' in geom and not 'FINAL_MESH' in geom:
		message = '\n\nReseting macros and deleting hotpoints...\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Reseting Macros
		#_resetMacros()
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
		
		message = '\n\nChecking geometry... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		geom_issue = _check_geom(base_mesh, scons, tcons)
		if geom_issue:
			upper_frame('e')
			message = '\nGeometry not ok. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			message = '\nSaving geometry...\n'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			# Get internal messages
			m = utils.Messenger()
			m.start_buffering()
			# Saving database visible as
			base.SaveVisibleAs(ansa.ScriptCurrentDir() + name + '__GEOM_PROBLEM.ansa')
			m.stop_buffering()
			ret_buffer = m.get_buffer()
			# Write internal messages to log file
			for i in ret_buffer:
				message = i + '\n'
				print_message(os.path.join(gdir, log_file), message, 0, 'b')
			m.clear()
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
		
		# Setting symmetry zpne type to the PID named "BDRY_SYM"
		message = '\n\nSetting symmetry zone type to the PID named BDRY_SYM.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		for pid in pids:
			if pid._name == 'BDRY_SYM':
				base.SetEntityCardValues(deck, pid, {'TYPE':'symmetry'})

		# Setting internal zone type to the PIDs that contains "_FTP" (Flow-Through-Plane) or "_DSK" (Proppeler Disk).
		message = '\n\nSetting internal zone type to the PID named _FTP or _DSK.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		#internal_pid_names = ['_INL', '_OUL', '_FWT', '_DSK']
		internal_pid_names = ['_FTP', '_DSK']
		internal_pids = []
		for pid in pids:
			if any(i in pid._name for i in internal_pid_names):
				internal_pids.append(pid)
		for pid in internal_pids:
			base.SetEntityCardValues(deck, pid, {'TYPE':'internal'})
		# Inlet and outlet boundary condition pid names
		inlet_outlet_bc_names = ['_INL', '_OUL']
		inlet_outlet_bc_pids = []
		for pid in pids:
			if any(i in pid._name for i in inlet_outlet_bc_names):
				inlet_outlet_bc_pids.append(pid)
		# Merge duplicate PID names into one single PID
		Merge_PIDs_Same_Name()
		
		
		message = '\nSaving geometry...\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Saving database visible as
		base.SaveVisibleAs(ansa.ScriptCurrentDir() + name + '__GEOM.ansa')
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
	
	# t2 here is a test
	t2 = time.time()
	
	t3 = time.time()
	
	if mesh_type == 1:
		message = '\n\nTime...........................:' + str('{:5.2f}'.format((t3 - t0)/60)) + ' minutes'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	elif blade_mesh:
		message = '\n\nTime...........................:' + str('{:5.2f}'.format((t3 - t2)/60)) + ' minutes'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	elif not blade_mesh:
		message = '\n\nTime...........................:' + str('{:5.2f}'.format((t3 - t0)/60)) + ' minutes'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		
		
		
	# Merging the hexa block mesh
	if os.path.isfile('hexa_block.ansa'):
		message = '\n\nMerging hexa block mesh... \n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		# Get internal messages
		m = utils.Messenger()
		m.start_buffering()
		# Merge file 
		utils.Merge("./hexa_block.ansa")
		# Stop internal messages
		m.stop_buffering()
		ret_buffer = m.get_buffer()
		# Write internal messages to log file
		for i in ret_buffer:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		m.clear()
		message = 'Hexa block mesh merged.\n\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	# #################################################################################################
	# Temporary until script modifications to deal with light volume representation
	# #################################################################################################
	# De-activate light volume representation for hexa block mesh
	base.SetANSAdefaultsValues({'HEXA_BLOCK_LIGHT_VOLUME_REPRESENTATION':'false'})
	message = '\nHexa block light volume representation de-activated.'
	print_message(os.path.join(gdir, log_file), message, 0, 'b')
	# De-activate light volume representation for volume mesh
	base.SetANSAdefaultsValues({'light_volume_representation':'false'})
	message = '\nGlobal Light volume representation de-activated.'
	print_message(os.path.join(gdir, log_file), message, 0, 'b')
	# #################################################################################################	
		
	# Shell Block Mesh
	hexa_box_faces = base.CollectEntities(deck, None, 'HEXA_BOX_FACE')
	if hexa_box_faces:
		message = '\n\n\n\n'\
		'############################################################################################################\n'\
		'############################################  HEXA BLOCK MESH   ############################################\n'\
		'############################################################################################################\n'\
		'\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'h')
		
		message = '\n\nRunning shell block mesh... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		associated_box_faces = []
		box_faces = []
		for hexa_box_face in hexa_box_faces:
			associated = base.GetEntityCardValues(deck, hexa_box_face, ['Associated'])['Associated']
			if associated == "YES":
				associated_box_faces.append(hexa_box_face)
			else:
				box_faces.append(hexa_box_face)
				
		hexa_box_edges = base.CollectEntities(deck, None, 'HEXA_BOX_EDGE')
		associated_box_edges = []
		box_edges = []
		for hexa_box_edge in hexa_box_edges:
			associated = base.GetEntityCardValues(deck, hexa_box_edge, ['Associated'])['Associated']
			if associated == "YES":
				associated_box_edges.append(hexa_box_edge)
				connected_nodes = base.GetEntityCardValues(deck, hexa_box_edge, ['Connect nodes to CONS'])['Connect nodes to CONS']
				if connected_nodes == "NO":
					message = '\nWarning: Found box edge nodes not connected to CONS.'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
			else:
				box_edges.append(hexa_box_edge)
		if not associated_box_edges: 
			message = '\nWarning: No edge association found.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
		if associated_box_faces:
			#ret1 = mesh.HexaBlockShellMesh(associated_box_faces, project=True, tolerance="0.01", apply_surface_fit=True, project_non_associated=True)
			#True funciona quando tem so uma simetria e nenhuam parede associada
			ret1 = mesh.HexaBlockShellMesh(associated_box_faces, project=True, tolerance="0.01", apply_surface_fit=True, project_non_associated=False)
		else:
			ret1 = False
			message = '\nWarning: No face association found.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		ret2 = mesh.HexaBlockShellMesh(box_faces, project=False)
		
		if ret1 or ret2:
			pshells = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
			for pshell in pshells:
				pname = base.GetEntityCardValues(deck, pshell, ['Name'])['Name']
				if pname == 'Default PSHELL Property':
					val = {'Name':'_SHELL_BLOCK'}
					base.SetEntityCardValues(deck, pshell, val)
					cells = base.GetEntityCardValues(deck, pshell, ['Num.Elem'])['Num.Elem']
					message = '\nShell block mesh done.'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					message = '\nPID name: _SHELL_BLOCK  ' + str(cells) + ' cells'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					
					message = '\nPID _SHELL_BLOCK is set to not be used in model.\nThe reason for this is to avoid having to specify a boundary condition to it.'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					base.SetEntityCardValues(deck, pshell, {'USE_IN_MODEL':'NO'})
		else:
			upper_frame('e')
			message = '\nShell block mesh fail. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
		
		# Freeze all hexa box faces
		base.FacesFreezeUnFreeze(faces=hexa_box_faces)
	
	# Hexa Block Mesh 
	if hexa_box_faces:
		base.FacesFreezeUnFreeze(faces=hexa_box_faces, unfreeze=True)
		message = '\n\nRunning hexa block mesh... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		hexa_boxes = base.CollectEntities(constants.OPENFOAM, None, 'HEXA_BOX')
		ret = mesh.HexaBlockVolumes(boxes=hexa_boxes, project=False)
		base.FacesFreezeUnFreeze(faces=hexa_box_faces)
		if ret:
			psolids = base.CollectEntities(deck, None, 'SOLID_PROPERTY')
			for psolid in psolids:
				pname = base.GetEntityCardValues(deck, psolid, ['Name'])['Name']
				if pname == 'Hexa Block Volumes "AUTO"':
					val = {'Name':'_HEXA_BLOCK'}
					base.SetEntityCardValues(deck, psolid, val)
					cells = base.GetEntityCardValues(deck, psolid, ['Num.Elem'])['Num.Elem']
					message = '\nHexa block mesh done.'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					message = '\nPID name: _HEXA_BLOCK  ' + str(cells) + ' cells'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					hexa_psolid = psolid
					base.Not(hexa_psolid)
					base.Not(hexa_boxes)
		else:
			upper_frame('e')
			message = '\nHexa block mesh fail. Abort! Abort!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('e')
			# Quit ANSA
			quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
	
	t4 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t4 - t3)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	#quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
	
	if not 'SURF_MESH' in geom and not 'LAYERS_MESH' in geom and not 'FINAL_MESH' in geom:
		message = '\n\n\n\n'\
		'############################################################################################################\n'\
		'##############################################  SURFACE MESH  ##############################################\n'\
		'############################################################################################################\n'\
		'\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'h')
		
		# Fluent deck
		deck = constants.FLUENT
		
		# Switch to mesh menu
		base.SetCurrentMenu('MESH')
		# Set default mesh element type
		base.SetANSAdefaultsValues({'element_type': 'tria'})
		
		# Autoload batch scenarios. 
		# The batch mesh filters are taken into account to distribute the model PIDs to batch mesh scenarios and sessions
		batchmesh.DistributeAllItemsToScenarios()
		
		# Run Surface mesh
		Surf_Mesh_Scenarios = base.CollectEntities(deck, None, 'BATCH_MESH_SESSION_GROUP')
		for Surf_Mesh_Scenario in Surf_Mesh_Scenarios:
			scenario = base.GetEntityCardValues(deck, Surf_Mesh_Scenario, ['Name'])
			filter_name = 'Surface_Mesh_Scenario'
			if scenario['Name'] == filter_name:
				message = '\n\nRunning surface mesh: ' + filter_name + '\nPlease wait.\n.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				# Run batch mesh scenario surface mesh
				status = batchmesh.RunMeshingScenario(Surf_Mesh_Scenario)
				m.stop_buffering()
				ret_buffer = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
				if status == 0: print_message(os.path.join(gdir, log_file), '\nScenario is deactivated.', 1, 'b')
				if status == 1: print_message(os.path.join(gdir, log_file), '\nScenario has run.', 1, 'b')
				if status == 2: print_message(os.path.join(gdir, log_file), '\nScenario has not run.', 1, 'b')
				# Check and Fix surface mesh
				if not base_mesh:
				    # Commented for automatic anisotropic mesh
					_check_fix_Quality()
					_fix_tria_on_corners()
					#_check_fix_Intersections()
					_check_fix_Sharp()
				else:
					base.Or(geom_pids)
					# Commented for automatic anisotropic mesh
					_check_fix_Quality()
					_fix_tria_on_corners()
					#_check_fix_Intersections()
					_check_fix_Sharp()
					base.All()
				# Hide hexablock boxes and solid elements
				if hexa_box_faces:
					base.Not(hexa_psolid)
					base.Not(hexa_boxes)
				# Unfreeze visible faces
				base.UnFreezeVisibleFaces()
				
				# Check nodes away from symmetry plane and fix it
				message = '\n\nChecking for nodes away from symmetry plane ...'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				checkSymmetry()
				
				message = '\nSaving surface mesh...\n'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				# Saving database visible as
				surf_mesh_filename = name + '__SURF_MESH.ansa.gz'
				base.SaveVisibleAs(ansa.ScriptCurrentDir() + surf_mesh_filename)
				m.stop_buffering()
				ret_buffer = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
	
	t5 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t5 - t4)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	# Morphing mesh
	if morph_mode == 1 or morph_mode == 2 or morph_mode == 3:

		morph_params = [morph_param_01, morph_param_02, morph_param_03, morph_param_04, morph_param_05, morph_param_06, morph_param_07, morph_param_08, morph_param_09, morph_param_10, morph_param_11, morph_param_12]
		morphing_parameters = base.CollectEntities(deck, None, 'PARAMETERS')
		
		if morph_mode == 1 or morph_mode == 3: name = name + '_m'
		
		idx_mcs=0
		if morph_mode == 3:
			for param in morphing_parameters:
				if param._name.startswith("RUDDER_") or param._name.startswith("ELEVATOR_") or param._name.startswith("AILERON_") or param._name.startswith("FLAP_"):
					idx_mcs=morphing_parameters.index(param)
					break

		# 1. Find index of last non‑zero (or -1 if all zero)
		last = max((i for i, v in enumerate(morph_params) if v != 0), default=-1)
		# 2. Build filename
		if last == -1:
			name = name           # no non-zero values
		else:
			parts = morph_params[: last + 1]  # include leading zeros up to last non-zero
			#name = name + "_" + "_".join(str(v) for v in parts)
			count=0
			for v in parts:
				if count == idx_mcs and morph_mode > 1:
					name = name + '_mcs'
				name = name + "_" +  str(v)
				count += 1
			
		if not all(v == 0 for v in morph_params):
			message = '\n\n\n\n'\
			'############################################################################################################\n'\
			'#############################################  MORPHING MESH  ##############################################\n'\
			'############################################################################################################\n'\
			'\n'
			print_message(os.path.join(gdir, log_file), message, 1, 'h')
			
			deck = constants.OPENFOAM
			shells = base.CollectEntities(constants.NASTRAN, None, "SHELL", filter_visible=True)
			morph_boxes = base.CollectEntities(deck, None, "MORPHBOX")
			morph.MorphLoad(morph_boxes, entities_to_load=shells, db_or_visib="Visib")
			morph.MorphFlagStatus("MORPHING_FLAG", True)
			morph.MorphFlagStatus("MORPH_FORCE_FROZEN_ENTS", True)
			disp = ""
			i=1

			for part in parts:
				for param in morphing_parameters:
					if param._id == i:
						message = '\nParameter ID: ' + str(param._id) + '  Parameter name: ' + str(param._name) + '  Displacement: ' + str(part)
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						if part != 0:
							morph.MorphParam(base.GetEntity(0, "PARAMETERS", param._id), part)
							disp += str('%+g' % part)
				i+=1
				
			message = '\nSaving surface mesh...\n'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			# Get internal messages
			m = utils.Messenger()
			m.start_buffering()
			# Delete previuos saved surface mesh file
			os.remove(os.path.join(gdir, surf_mesh_filename))
			# Saving database visible as
			#name = name + disp
			surf_mesh_filename = name + '__SURF_MESH.ansa.gz'
			base.SaveVisibleAs(ansa.ScriptCurrentDir() + name + '__SURF_MESH.ansa.gz')
			m.stop_buffering()
			ret_buffer = m.get_buffer()
			# Write internal messages to log file
			for i in ret_buffer:
				message = i + '\n'
				print_message(os.path.join(gdir, log_file), message, 0, 'b')
			m.clear()
		
	
	if not 'LAYERS_MESH' in geom and not 'FINAL_MESH' in geom:
		message = '\n\n\n\n'\
		'############################################################################################################\n'\
		'##############################################  LAYERS MESH  ###############################################\n'\
		'############################################################################################################\n'\
		'\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'h')
		
		# Fluent deck
		deck = constants.FLUENT
		
		# Run Layers mesh
		Layers_Mesh_Scenarios = base.CollectEntities(deck, None, 'BATCH_MESH_LAYERS_SCENARIO')
		for Layers_Mesh_Scenario in Layers_Mesh_Scenarios:
			scenario = base.GetEntityCardValues(deck, Layers_Mesh_Scenario, ['Name'])
			if mesh_type == 1:
				filter_name = 'Layers_Mesh_Scenario'
			else:
				filter_name = 'Layers_Mesh_Scenario_Propeller_Blades'
			if scenario['Name'] == filter_name:
				message = '\n\nRunning layers mesh: ' + filter_name + '\nPlease wait.\n.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				# Run batch mesh scenario layers mesh
				status = batchmesh.RunMeshingScenario(Layers_Mesh_Scenario)
				m.stop_buffering()
				ret_buffer_layers_scenario = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer_layers_scenario:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
				if status == 0: print_message(os.path.join(gdir, log_file), '\nScenario is deactivated.', 1, 'b')
				if status == 1: print_message(os.path.join(gdir, log_file), '\nScenario has run.', 1, 'b')
				if status == 2: print_message(os.path.join(gdir, log_file), '\nScenario has not run.', 1, 'b')
				# Hide hexablock boxes and solid elements
				if hexa_box_faces:
					base.Not(hexa_psolid)
					base.Not(hexa_boxes)
				message = '\nSaving layers mesh...\n'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				# Saving database visible as
				base.SaveVisibleAs(ansa.ScriptCurrentDir() + name + '__LAYERS_MESH.ansa.gz')
				m.stop_buffering()
				ret_buffer = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
				
				# Check internal messages og layers scenario
				for i in ret_buffer_layers_scenario:
					if i.startswith('Problematic areas detected'):
						upper_frame('e')
						message = '\n' + i + '. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
					if 'Layers generation stopped at layer' in i:
						upper_frame('e')
						message = '\n' + i + '. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
					if 'No Layers generated' in i:
						upper_frame('e')
						message = '\n' + i + '. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)

				# Check if layers mesh exists
				all_vols = base.CollectEntities(deck, None, 'VOLUME')
				for vol in all_vols:
					vol_vals = base.GetEntityCardValues(deck, vol, ['Status', 'Type'])
					if vol_vals['Type'] == "Layers" and vol_vals['Status'] == "Unmeshed":
						upper_frame('e')
						message = '\nLayers mesh sceario ended with status Unmeshed. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
						
				# Check status
				#if status == 2:
				#	upper_frame('e')
				#	message = '\nScenario has not run. Abort! Abort!'
				#	print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#	lower_frame('e')
				#	# Quit ANSA
				#	quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
						
		message = '\nLayers mesh scenario completed!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		
		# Set the volume calculation method 
		#if int(ansa_main_version) >= 21:
		#	vol_calc_method = 'CFD++ PARTIAL'
		#	#vol_calc_method = 'PARTIAL'
		#else:
		#	vol_calc_method = 'PARTIAL'
			
		# Check and fix negative volume
		vol_calc_method = 'PARTIAL'
		base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
		message = '\n\nChecking layers mesh for negative volume... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_partial = _checkNegative(vol_calc_method)
		
		vol_calc_method = 'OPENFOAM PARTIAL'
		base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
		message = '\n\nChecking layers mesh for negative volume... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_openfoam_partial = _checkNegative(vol_calc_method)
		
		vol_calc_method = 'CFD++ PARTIAL'
		base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
		negvol_cfdpp_partial_layers = 0
		message = '\n\nChecking layers mesh for negative volume... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_cfdpp_partial = _checkNegative(vol_calc_method)
		
		vol_calc_method = 'FLUENT'
		base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
		negvol_fluent_layers = 0
		message = '\n\nChecking layers mesh for negative volume... Please wait.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_fluent = _checkNegative(vol_calc_method)
		
		if neg_vol_check_cfdpp_partial != 0:
			negvol_cfdpp_partial_layers = 1
			#message = '\nYou will have a better chance during volume quality improvement.'
			#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	t6 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t6 - t5)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	# Check and Fix intersections
	#_check_fix_Intersections()
	
	if not 'FINAL_MESH' in geom:
		message = '\n\n\n\n'\
		'############################################################################################################\n'\
		'##############################################  VOLUME MESH  ###############################################\n'\
		'############################################################################################################\n'\
		'\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'h')
		
		# Fluent deck
		deck = constants.FLUENT
		
		# Run Volume mesh
		Volume_Mesh_Scenarios = base.CollectEntities(deck, None, 'BATCH_MESH_VOLUME_SCENARIO')
		for Volume_Mesh_Scenario in Volume_Mesh_Scenarios:
			scenario = base.GetEntityCardValues(deck, Volume_Mesh_Scenario, ['Name'])
			filter_name = 'Volume_Mesh_Scenario'
			if scenario['Name'] == filter_name:
				sessions = batchmesh.GetSessionsFromMeshingScenario(Volume_Mesh_Scenario)
				prop_volume = 0
				for session in sessions:
					if session._name == 'PROPELLER_VOLUME':
						prop_volume = 1
						if mesh_type == 2:
							batchmesh.SetBatchMeshItemActiveState(session, active_state=True)
						else:
							batchmesh.SetBatchMeshItemActiveState(session, active_state=False)
					#if session._name == 'GAP_VOLUME':
						#batchmesh.SetBatchMeshItemActiveState(session, active_state=False)
				if mesh_type == 2 and prop_volume == 0:
					upper_frame('e')
					message = '\nPROPELLER_VOLUME session not found in Volume_Mesh_Scenario. Abort! Abort!'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					lower_frame('e')
					# Quit ANSA
					quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
					
				message = '\n\nRunning volume mesh: ' + filter_name + '\nPlease wait.\n.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				# Run batch mesh scenario volume mesh
				status = batchmesh.RunMeshingScenario(Volume_Mesh_Scenario)
				m.stop_buffering()
				ret_buffer_volume_scenario = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer_volume_scenario:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
				if status == 0: print_message(os.path.join(gdir, log_file), '\nScenario is deactivated.', 1, 'b')
				if status == 1: print_message(os.path.join(gdir, log_file), '\nScenario has run.', 1, 'b')
				if status == 2: print_message(os.path.join(gdir, log_file), '\nScenario has not run.', 1, 'b')
				message = '\nSaving final mesh...\n'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				# Get internal messages
				m = utils.Messenger()
				m.start_buffering()
				# Saving database
				base.SaveAs(ansa.ScriptCurrentDir() + name + '__FINAL_MESH.ansa.gz')
				m.stop_buffering()
				ret_buffer = m.get_buffer()
				# Write internal messages to log file
				for i in ret_buffer:
					message = i + '\n'
					print_message(os.path.join(gdir, log_file), message, 0, 'b')
				m.clear()
				
				# Check internal messages of volume mesh scenario
				for i in ret_buffer_volume_scenario:
					if 'Volume detection may be erroneous' in i:
						upper_frame('e')
						message = '\n' + i + '. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						#quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
					if 'Errors in volume boundary definition' in i:
						upper_frame('e')
						message = '\n' + i + '. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
					if '1 volumes failed to be meshed' in i:
						upper_frame('e')
						message = '\n' + i + '. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
						
				# Check if volume meshed with Tetra Rapid exists
				all_vols = base.CollectEntities(deck, None, 'VOLUME')
				for vol in all_vols:
					vol_vals = base.GetEntityCardValues(deck, vol, ['Status', 'Type'])
					if vol_vals['Type'] == "Tetra Rapid" and vol_vals['Status'] == "Unmeshed":
						upper_frame('e')
						message = '\nVolume mesh sceario ended with status Unmeshed. Abort! Abort!'
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						lower_frame('e')
						# Quit ANSA
						quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
				
				# Check status
				if status == 2:
					upper_frame('e')
					message = '\nScenario has not run. Abort! Abort!'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					lower_frame('e')
					# Quit ANSA
					quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
				
		message = "\nVolume mesh scenario completed!"
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	if base_mesh:
		final_vols = base.CollectEntities(deck, None, 'VOLUME')
	
	t7 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t7 - t6)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'#######################################  VOLUME QUALITY IMPROVEMENT  #######################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	# OPENFOAM deck
	deck = constants.OPENFOAM
	
	# Show only the new generated volume mesh.	
	if base_mesh:
		new_vols = list(set(final_vols).symmetric_difference(set(base_vols)))
		base.Or(new_vols)
		
	# Hide all PIDs of zone type WALL or SYMMETRY during volume quality improvement.
	message = '\n\nHiding all PIDs of zone type wall and symmetry.\nThese PIDs will be frozen during volume quality improvement.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
	for pid in pids:
		type_element = base.GetEntityCardValues(deck, pid, ['TYPE'])['TYPE']
		if type_element == 'wall' or type_element == 'symmetry':
			base.Not(pid)
	
	# Activate freeze non visible shells option
	message = '\nFreeze non visible shells activated.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.SetANSAdefaultsValues({'freeze_non_visible_shells':'true'})
			
	# Hide all Pure Hexa Block Mesh during volume quality improvement.		
	#all_vols = base.CollectEntities(deck, None, 'VOLUME')
	#for vol in all_vols:
	#	vol_vals = base.GetEntityCardValues(deck, vol, ['Status', 'Type'])
	#	if vol_vals['Type'] == "Hexa Block" and vol_vals['Status'] == "Meshed":
	#		base.Not(vol)
	
	# Inactivate all shell and solid quality criteria
	#_InactiveShellCriteria()
	#_InactiveSolidCriteria()
	
    # FLUENT deck
	deck = constants.FLUENT
    
	# Use the UDF SetQualityCriteria to "feed" F11 and Deck info with proper quality check criteria
	# # Aerospace or OpenFOAM
	# quality_criteria_solver = 'Aerospace'
	# SetQualityCriteria_main(False, quality_criteria_solver, 'Relaxed', True)
	# SetQualityCriteria_main(False, quality_criteria_solver, 'Strict', True)
	# Set Aerospace quality criteria Fluent
	message = '\n\nSetting Aerospace quality criteria y+1 FLUENT'
	if major == 24:
		sq(gui = False, old_gui = False, solver = 'Fluent', application = 'Aerospace', layer = 'y+ 1', poly_mesh = False, hextreme = False)
	if major == 25:
		SetQualityCriteria.SetQualityCriteria_main(gui = False, old_gui = False, solver = 'Fluent', application = 'Aerospace', layer = 'y+ 1', poly_mesh = False, hextreme = False)
	

	# Set and start Improve Quality Volume
	message = '\n\nRunning Improve Quality Volume... Please wait.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	#message = '\n\nQuality criterias:'
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
    #
	#_InactiveShellCriteria()
	#_InactiveSolidCriteria()
	## Maximum non orthogonality for FLUENT should be < 0.01.
	non_orthog = 0.05
	non_orthog_type = 'FLUENT'
	message = '\n  - Maximum non orthogonality of a solid element : ' + str(non_orthog) + '  ' + non_orthog_type 
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.F11SolidsOptionsSet('non orthogonality', True, non_orthog_type, non_orthog)
	#
	## Maximum warping angle of the quad facets of a solid element. 10 strict, 20 medium, 30 high.
	#warp_solid = 20
	#warp_type = 'IDEAS'
	#message = '\n  - Maximum warping angle of the quad facets of a solid element : ' + str(warp_solid) + '  ' + warp_type 
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11SolidsOptionsSet('warping', True, warp_type, warp_solid)
	#
	## Maximum solid angle ratio between facets for penta elements. Angle ratio = 0 for a perfect penta (quad or tria facets).
	#maxang_pen = 0.98
	#maxang_pen_type = 'FLUENT'
	#message = '\n  - Maximum solid angle ratio between facets for penta elements : ' + str(maxang_pen) + '  ' + maxang_pen_type 
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11SolidsOptionsSet('max angle pentas', True, maxang_pen_type, maxang_pen)
	#
	## Maximum solid angle ratio between facets for hexa elements. Angle ratio = 0 for a perfect hexa (quad facet only).
	#maxang_hex = 0.98
	#maxang_hex_type = 'FLUENT'
	#message = '\n  - Maximum solid angle ratio between facets for hexa elements : ' + str(maxang_hex) + '  ' + maxang_hex_type 
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11SolidsOptionsSet('max angle hexas', True, maxang_hex_type, maxang_hex)
	#
	## Maximum solid skewness for tetra elements. Skewness = 0 for a perfect tetra.
	skew_solid = 0.95
	skew_solid_type = 'FLUENT'
	message = '\n  - Maximum solid skewness for tetra elements : ' + str(skew_solid) + '  ' + str(skew_solid_type) 
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.F11SolidsOptionsSet('skewness', True, skew_solid_type, skew_solid)
	#
	## Maximum shell skewness for tria elements. Skewness = 0 for a perfect tria.
	#skew_shell = 0.85
	#skew_shell_type = 'FLUENT'
	#message = '\n  - Maximum shell skewness for tria elements : ' + str(skew_shell) + '  ' + str(skew_shell_type) 
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11ShellsOptionsSet('skewness', True, skew_shell_type, skew_shell)
	#
	# Maximum distance from external bounds that a node is allowed to move.
	message = '\n\nMaximum distance from external bounds that a node is allowed to move: '
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	nodes_move_distance = '0.6*local'
	message = '\n  - Maximum external bounds distance ' + str(nodes_move_distance) + '\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.SetANSAdefaultsValues({'maximum_distance_from_external_bounds':nodes_move_distance})
	#
	## Left handed
	#message = '\n  - Left handed volume. Inverted volume elements with flipped facets pointing inwards.'
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11SolidsOptionsSet('left handed', True, '', 0)
	#
	## Fix quality
	#vol_calc_method = 'PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	## Fix quality
	#vol_calc_method = 'OPENFOAM PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	# Fix quality 
	vol_calc_method = 'CFD++ PARTIAL'
	_fix_quality_volume(vol_calc_method, nodes_move_distance)
	
	#message = '\n\n  2nd pass.'
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#
	## Fix quality 
	#vol_calc_method = 'PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	## Fix quality 
	#vol_calc_method = 'OPENFOAM PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	## Fix quality 
	#vol_calc_method = 'CFD++ PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	#message = '\n\n  3rd pass.'
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#
	## Fix quality 
	#vol_calc_method = 'PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	## Fix quality 
	#vol_calc_method = 'OPENFOAM PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	#
	## Fix quality 
	#vol_calc_method = 'CFD++ PARTIAL'
	#_fix_quality_volume(vol_calc_method, nodes_move_distance)
	

	# Bring everything to visible
	#base.All()
	
	t8 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t8 - t7)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'######################################  CHECK AND FIX NEGATIVE VOLUME  #####################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	# Check and Fix intersections
	#_check_fix_Intersections()
	
	negvol_cfdpp_partial_final = 0
	negvol_cfdpp_total_final = 0
	negvol_fluent_final = 0
	
	# First check: Auto fix
	message = '\n\n  First check: Auto fix.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	vol_calc_method = 'PARTIAL'
	base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
	message = '\n\nChecking and fixing negative volume... Please wait.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	neg_vol_check_partial = _check_neg_vols_and_auto_fix(vol_calc_method)
	
	vol_calc_method = 'OPENFOAM PARTIAL'
	base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
	message = '\n\nChecking and fixing negative volume... Please wait.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	neg_vol_check_openfoam_partial = _check_neg_vols_and_auto_fix(vol_calc_method)
	
	vol_calc_method = 'CFD++ PARTIAL'
	base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
	message = '\n\nChecking and fixing negative volume... Please wait.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	neg_vol_check_cfdpp_partial = _check_neg_vols_and_auto_fix(vol_calc_method)
	
	vol_calc_method = 'CFD++ TOTAL'
	base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
	message = '\n\nChecking and fixing negative volume... Please wait.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	neg_vol_check_cfdpp_total = _check_neg_vols_and_auto_fix(vol_calc_method)

	vol_calc_method = 'FLUENT'
	base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
	message = '\n\nChecking and fixing negative volume... Please wait.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	neg_vol_check_cfdpp_total = _check_neg_vols_and_auto_fix(vol_calc_method)	
	
	# Second check: Fill the void
	fix_negative_vol_fill_void_cfdpp_partial = 1
	fix_negative_vol_fill_void_openfoam_partial = 1
	fix_negative_vol_fill_void_partial = 1
	fix_negative_vol_fill_void_fluent = 1
	if neg_vol_check_cfdpp_total != 0:
		if neg_vol_check_cfdpp_partial != 0 or neg_vol_check_openfoam_partial != 0 or neg_vol_check_partial != 0:
			message = '\n\n\n\n  Second check: Fill the void.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			
		if neg_vol_check_cfdpp_partial != 0:
			vol_calc_method = 'CFD++ PARTIAL'
			base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
			message = '\n\nChecking and fixing negative volume... Please wait.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			fix_negative_vol_fill_void_cfdpp_partial = _fix_negvol_fill_void(vol_calc_method)
			if base_mesh:
				base.Or(new_vols)
			else:
				base.All()
			
		if neg_vol_check_openfoam_partial != 0:
			vol_calc_method = 'OPENFOAM PARTIAL'
			base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
			message = '\n\nChecking and fixing negative volume... Please wait.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			fix_negative_vol_fill_void_openfoam_partial = _fix_negvol_fill_void(vol_calc_method)
			if base_mesh:
				base.Or(new_vols)
			else:
				base.All()
			
		if neg_vol_check_partial != 0:
			vol_calc_method = 'PARTIAL'
			base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
			message = '\n\nChecking and fixing negative volume... Please wait.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			fix_negative_vol_fill_void_partial = _fix_negvol_fill_void(vol_calc_method)
			if base_mesh:
				base.Or(new_vols)
			else:
				base.All()

		if neg_vol_check_partial != 0:
			vol_calc_method = 'FLUENT'
			base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
			message = '\n\nChecking and fixing negative volume... Please wait.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			fix_negative_vol_fill_void_fluent = _fix_negvol_fill_void(vol_calc_method)
			if base_mesh:
				base.Or(new_vols)
			else:
				base.All()
				
	# Final check: Auto fix. 
	message = '\n\n\n\n  Final check: Auto fix.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
	vol_calc_method = 'PARTIAL'
	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\n\nNegative volume remains. Last try.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_partial = _check_neg_vols_and_auto_fix(vol_calc_method)
		if neg_vol_check_partial != 0:
			message = '\n\nNegative volume remains. Not good.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
	vol_calc_method = 'OPENFOAM PARTIAL'
	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\n\nNegative volume remains. Last try.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_openfoam_partial = _check_neg_vols_and_auto_fix(vol_calc_method)
		if neg_vol_check_openfoam_partial != 0:
			message = '\n\nNegative volume remains. Not good.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
	vol_calc_method = 'CFD++ PARTIAL'
	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\n\nNegative volume remains. Last try.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_cfdpp_partial = _check_neg_vols_and_auto_fix(vol_calc_method)
		if neg_vol_check_cfdpp_partial != 0:
			message = '\n\nNegative volume remains. Not good.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			negvol_cfdpp_partial_final = 1
		
	vol_calc_method = 'CFD++ TOTAL'
	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\n\nNegative volume remains. Last try.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_cfdpp_total = _check_neg_vols_and_auto_fix(vol_calc_method)
		if neg_vol_check_cfdpp_total != 0:
			message = '\n\nNegative volume remains. Not good.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			negvol_cfdpp_total_final = 1

	vol_calc_method = 'FLUENT'
	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\n\nNegative volume remains. Last try.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		neg_vol_check_fluent = _check_neg_vols_and_auto_fix(vol_calc_method)
		if neg_vol_check_fluent != 0:
			message = '\n\nNegative volume remains. Not good.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			negvol_fluent_final = 1	
	
	
	t9 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t8 - t7)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'##############################################  SAVING MESH  ###############################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
		
	# Bring everything to visible
	base.All()
	
	# Convert to light representation volume
	allvolumes = base.CollectEntities(constants.NASTRAN, None, 'VOLUME')
	message = 'Converting all volumes to light volume representation' + '\n\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	for vol in allvolumes:
		ret = mesh.ConvertToLightVolumeRepresentation(vol)
	
	# Set volume PID
	message = '\n\nSetting PID volume... Please wait.\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	Fluid_pids='Fluid'
	_SetPidVolume(Fluid_pids)
	
	
	# #############################################################################################################
	# This is specific to the HLPW convention work.
	# HLPW bc names list
	bcnames = ['W-RH', 'P-RH', 'N-RH', 'T-RH', 'W.FLP-00-RH', 'W.FLP-01-RH', 'W.SLT-00-RH', 'W.SLT-01-RH', 'B-RH', 'BDRY_SYM', 'BDRY_FAR']
	# Startswith filters list corresponding to the bc names list
	sw_filters  = ['W_', 'P_', 'N_', 'T_', 'W.FLP', 'W.FLP', 'W.SLT', 'W.SLT', 'B_', 'BDRY_SYM', 'BDRY_FAR']
	# Contains filters list corresponding to the bc names list
	co_filters  = ['', '', '', '', '-IB', '-OB', '-IB', '-OB', '', '', '']
	# Set bc names acoording to HLPW convention
	#hlpw_bcnames(bcnames, sw_filters, co_filters)
	# #############################################################################################################

	
	# Compressing unused entities
	message = '\n\nCompressing unused entities... Please wait\n.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Compressing
	base.Compress('')
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	
	# Print final shell names
	message = '\n\nUsed in BC file?  Shell names\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	pids_shell = base.CollectEntities(constants.OPENFOAM, None, 'SHELL_PROPERTY')
	pids_solid = base.CollectEntities(constants.OPENFOAM, None, 'SOLID_PROPERTY')
	wall_pids = []
	wall_ids = []
	Symmetry_pids = []
	Symmetry_ids = []
	Farfield_pids = []
	Farfield_ids = []
	Prop_Disk_pids = []
	Prop_Disk_ids = []
	Fan_Inlet_pids = []
	Fan_Inlet_ids = []
	Fan_Outlet_pids = []
	Fan_Outlet_ids = []
	Core_Outlet_pids = []
	Core_Outlet_ids = []
	Flow_Thru_Plane_pids = []
	Flow_Thru_Plane_ids = []
	Ground_pids = []
	Ground_ids = []
	Fluid_pids = []
	Fluid_ids = []
	zone_pids = ["BDRY_FAR", "BDRY_SYM", "BDRY_GRD"]
	for internal_pid in internal_pids:
		zone_pids.append(internal_pid._name)
	for inlet_outlet_bc_pid in inlet_outlet_bc_pids:
		zone_pids.append(inlet_outlet_bc_pid._name)	
		
	for pid in pids_shell:
		use_in_model = base.GetEntityCardValues(constants.OPENFOAM, pid, ['USE_IN_MODEL'])['USE_IN_MODEL']
		message = use_in_model + '                ' + pid._name + '\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		if use_in_model == "YES":
			if not any (i in pid._name for i in zone_pids):
				wall_pids.append(pid._name)
				wall_ids.append(pid._id)
		if use_in_model == "YES" and pid._name == 'BDRY_SYM':
			Symmetry_pids.append(pid._name)
			Symmetry_ids.append(pid._id)
		if use_in_model == "YES" and pid._name == 'BDRY_FAR':
			Farfield_pids.append(pid._name)
			Farfield_ids.append(pid._id)
		if use_in_model == "YES" and pid._name.startswith('X'):
			Prop_Disk_pids.append(pid._name)
			Prop_Disk_ids.append(pid._id)
		if use_in_model == "YES" and "_INL" in pid._name:
			Fan_Inlet_pids.append(pid._name)
			Fan_Inlet_ids.append(pid._id)
		if use_in_model == "YES" and "_OUL-COLD" in pid._name:
			Fan_Outlet_pids.append(pid._name)
			Fan_Outlet_ids.append(pid._id)
		if use_in_model == "YES" and "_OUL-HOT" in pid._name:
			Core_Outlet_pids.append(pid._name)
			Core_Outlet_ids.append(pid._id)
		if use_in_model == "YES" and "_FTP" in pid._name:
			Flow_Thru_Plane_pids.append(pid._name)
			Flow_Thru_Plane_ids.append(pid._id)
		if use_in_model == "YES" and pid._name.startswith('BDRY_GRD'):
			Ground_pids.append(pid._name)
			Ground_ids.append(pid._id)
		
		
	for pid in pids_solid:
		if pid._name == 'Fluid':
			Fluid_pids.append(pid._name)
			Fluid_ids.append(pid._id)
			
	message = '\nWall PIDs: ' + " ".join(wall_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nWall IDs: ' + " ".join(str(wall_id) for wall_id in wall_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nSymmetry PIDs: ' + " ".join(Symmetry_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nSymmetry IDs: ' + " ".join(str(Symmetry_id) for Symmetry_id in Symmetry_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFarfield PIDs: ' + " ".join(Farfield_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFarfield IDs: ' + " ".join(str(Farfield_id) for Farfield_id in Farfield_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nProp_Disk PIDs: ' + " ".join(str(Prop_Disk_pid) for Prop_Disk_pid in Prop_Disk_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nProp_Disk IDs: ' + " ".join(str(Prop_Disk_id) for Prop_Disk_id in Prop_Disk_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFan_Inlet PIDs: ' + " ".join(str(Fan_Inlet_pid) for Fan_Inlet_pid in Fan_Inlet_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFan_Inlet IDs: ' + " ".join(str(Fan_Inlet_id) for Fan_Inlet_id in Fan_Inlet_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFan_Outlet PIDs: ' + " ".join(str(Fan_Outlet_pid) for Fan_Outlet_pid in Fan_Outlet_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFan_Outlet IDs: ' + " ".join(str(Fan_Outlet_id) for Fan_Outlet_id in Fan_Outlet_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nCore_Outlet PIDs: ' + " ".join(str(Core_Outlet_pid) for Core_Outlet_pid in Core_Outlet_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nCore_Outlet IDs: ' + " ".join(str(Core_Outlet_id) for Core_Outlet_id in Core_Outlet_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFlow_Thru_Plane PIDs: ' + " ".join(str(Flow_Thru_Plane_pid) for Flow_Thru_Plane_pid in Flow_Thru_Plane_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFlow_Thru_Plane IDs: ' + " ".join(str(Flow_Thru_Plane_id) for Flow_Thru_Plane_id in Flow_Thru_Plane_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nGround PIDs: ' + " ".join(str(Ground_pid) for Ground_pid in Ground_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nGround IDs: ' + " ".join(str(Ground_id) for Ground_id in Ground_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFluid PIDs: ' + " ".join(Fluid_pids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFluid IDs: ' + " ".join(str(Fluid_id) for Fluid_id in Fluid_ids)
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nDimension: 3D\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	# This is specific for Fluent :( 
	# All the internal PIDs containing "_INL" or "_OUL" or "_FTH" will be split into two and the new one will have the name SHADOW appended at the end of the PID name. 
	# This function duplicates the selected shell properties and disconnects the volume mesh.
	#m.start_buffering()
	#ret = base.SplitVolumeMesh(internal_pids, 1)
	#m.stop_buffering()
	#ret_buffer = m.get_buffer()
	#if ret == 0:
	#	message = '\nSplit internal PIDs success!\n'
	#	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#	for i in ret_buffer:
	#		message = i + '\n'
	#		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	#else:
	#	message = '\nSplit internal PIDs failure!\n'
	#	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#	for i in ret_buffer:
	#		message = i + '\n'
	#		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	#m.clear()	
	
    ############# Last check and fix of neg vol before saving the final mesh
    # Some neg vols elements are not being captured by the current neg vol check and fix.
    # I need to rethink the logic 
	message = '\n\nFinal check neg vol auto fix\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	vol_calc_method = 'CFD++ PARTIAL'
	negvol = checks.mesh.NegativeVolume()
	negvol.calculation_method = vol_calc_method
	message = '\nCalculation method: ' + vol_calc_method
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	res = negvol.execute(exec_mode = Check.EXEC_ON_MODEL, report = Check.REPORT_NONE)
	report = res[0]
	if report.issues:
		for issue in report.issues:
			title = issue.description
			message = '\n' + title
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			message = '\nAttempting to fix negative elements.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			ents = issue.entities
			report.try_fix()	
			message = '\nChecking for negative volume elements again.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			negvol = checks.mesh.NegativeVolume()
			negvol.calculation_method = vol_calc_method
			res = negvol.execute(exec_mode = Check.EXEC_ON_MODEL, report = Check.REPORT_NONE)
			report = res[0]
			if report.issues:
				for issue in report.issues:
					title = issue.description
					message = '\n' + title
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Last check for Fluent
	vol_calc_method = 'FLUENT'
	_check_neg_vols_and_auto_fix(vol_calc_method)	
    ###############################################
    
	# Save final mesh
	message = '\n\nSaving final mesh...\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Saving database visible as
	base.SaveAs(ansa.ScriptCurrentDir() + name + '__FINAL_MESH.ansa.gz')
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	
	
	t10 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t10 - t9)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	

	
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'##############################################  OUTPUT MESH  ###############################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	# Fluent deck
	deck = constants.FLUENT
	
	# Output mesh
	#output_mesh_dir = 'CFDpp_Meters_' + name
	output_mesh_dir = '../Fluent_Meters_' + name
	Path(output_mesh_dir).mkdir(parents=True, exist_ok=True)
	message = '\n\nWriting solver output files to directory: ' + output_mesh_dir + '\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	outputUnits = utils.UnitSystem(length='meter')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Saving output mesh
	#base.OutputCFDPP(output_mesh_dir, mode = 'visible', unit_system = outputUnits)
	base.OutputFluent(os.path.join(output_mesh_dir, name), format = "hdf5", write_solver_info = "on", mode = 'visible', unit_system = outputUnits)
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	
	t11 = time.time()
	message = '\n\nTime...........................:' + str('{:5.2f}'.format((t11 - t10)/60)) + ' minutes'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	
	
	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'###############################################  STATISTICS  ###############################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	
	#message = '\n\nTotal Time...........................:' + str('{:5.2f}'.format((t11 - t0)/60)) + ' minutes'
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	# Print the time required for each step
	message = '\n\nTIME REQUIRED FOR EACH STEP: \n\n'\
			  'GEOMETRY.....................................: ' + str('{:6.2f}'.format((t3 - t0)/60))   + ' minutes \n'\
			  'HEXA BLOCK MESH..............................: ' + str('{:6.2f}'.format((t4 - t3)/60))   + ' minutes \n'\
			  'SURFACE MESH.................................: ' + str('{:6.2f}'.format((t5 - t4)/60))   + ' minutes \n'\
			  'LAYERS MESH..................................: ' + str('{:6.2f}'.format((t6 - t5)/60))   + ' minutes \n'\
			  'VOLUME MESH..................................: ' + str('{:6.2f}'.format((t7 - t6)/60))   + ' minutes \n'\
			  'VOLUME QUALITY IMPROVEMENT...................: ' + str('{:6.2f}'.format((t8 - t7)/60))   + ' minutes \n'\
			  'CHECK AND FIX NEGATIVE VOLUME................: ' + str('{:6.2f}'.format((t9 - t8)/60))   + ' minutes \n'\
			  'SAVING MESH..................................: ' + str('{:6.2f}'.format((t10 - t9)/60))  + ' minutes \n'\
			  'OUTPUT MESH..................................: ' + str('{:6.2f}'.format((t11 - t10)/60)) + ' minutes \n\n'\
			  'TOTAL TIME FOR THE WHOLE PROCESS.............: ' + str('{:6.2f}'.format((t11 - t0)/60))  + ' minutes \n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	
	# Number of solid elements
	vols = base.CollectEntities(deck, None, 'VOLUME')
	NTetra = 0
	NPenta = 0
	NHexa = 0
	NPyra = 0
	for vol in  vols:
		vol_tetras = base.GetEntityCardValues(deck, vol, ['Tetras'])['Tetras']
		NTetra += vol_tetras
		vol_pentas = base.GetEntityCardValues(deck, vol, ['Pentas'])['Pentas']
		NPenta += vol_pentas
		vol_hexas = base.GetEntityCardValues(deck, vol, ['Hexas'])['Hexas']
		NHexa += vol_hexas
		vol_pyramids = base.GetEntityCardValues(deck, vol, ['Pyramids'])['Pyramids']
		NPyra += vol_pyramids
	
	NSolids = NTetra + NPenta + NHexa + NPyra
	if NSolids > 0:
		NTetra_perc = (NTetra/NSolids)*100
		NPenta_perc = (NPenta/NSolids)*100
		NHexa_perc = (NHexa/NSolids)*100
		NPyra_perc = (NPyra/NSolids)*100
		
		
		message = '\n\n\nNUMBER OF SOLID ELEMENTS:\n\n'\
				  'TETRA........................................: ' + str('{:10.0f}'.format(NTetra)) + '  ' + str('{:3.0f}'.format(NTetra_perc)) + ' %\n'\
				  'PENTA........................................: ' + str('{:10.0f}'.format(NPenta)) + '  ' + str('{:3.0f}'.format(NPenta_perc)) + ' %\n'\
				  'HEXA.........................................: ' + str('{:10.0f}'.format(NHexa))  + '  ' + str('{:3.0f}'.format(NHexa_perc))  + ' %\n'\
				  'PYRAMID......................................: ' + str('{:10.0f}'.format(NPyra))  + '  ' + str('{:3.0f}'.format(NPyra_perc))  + ' %\n\n'\
				  'TOTAL........................................: ' + str('{:10.0f}'.format(NSolids))
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	#Create a surface mesh based on a provided CAD file for Fluent posproc only
	exit_plane_fan_out_1_geom = name + "_exit_plane_fan_out_1.CATPart"
	exit_plane_fan_out_2_geom = name + "_exit_plane_fan_out_2.CATPart"
	exit_plane_core_out_1_geom = name + "_exit_plane_core_out_1.CATPart"
	exit_plane_core_out_2_geom = name + "_exit_plane_core_out_2.CATPart"
	inlet_plane_fan_1_geom = name + "_inlet_plane_fan_1.CATPart"
	inlet_plane_fan_2_geom = name + "_inlet_plane_fan_2.CATPart"
	
	plane_geoms = [exit_plane_fan_out_1_geom, exit_plane_fan_out_2_geom, exit_plane_core_out_1_geom, exit_plane_core_out_2_geom, inlet_plane_fan_1_geom, inlet_plane_fan_2_geom]
	mesh_names = ["exit_plane_fan_out_1", "exit_plane_fan_out_2", "exit_plane_core_out_1", "exit_plane_core_out_2", "inlet_plane_fan_1", "inlet_plane_fan_2"]
	for i in range(len(plane_geoms)):
		if os.path.isfile(os.path.join(gdir, plane_geoms[i])):
			message = '\n\nIdentified mesh plane to be generated: ' + str(plane_geoms[i]) + '\n'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
			deck = constants.OPENFOAM
			base.Open(os.path.join(gdir, plane_geoms[i]))
			bscn_exit_plane="Batch_Scenario_exit_plane.ansa"
			utils.Merge(os.path.join(bdir, bscn_exit_plane), property_offset = 'offset')
			base.SetANSAdefaultsValues({'tolerance_mode':'fine'})
			
			Surf_Mesh_Scenarios = base.CollectEntities(deck, None, 'BATCH_MESH_SESSION_GROUP')
			for Surf_Mesh_Scenario in Surf_Mesh_Scenarios:
				scenario = base.GetEntityCardValues(deck, Surf_Mesh_Scenario, ['Name'])
				filter_name = 'Surface_Mesh_Scenario'
				if scenario['Name'] == filter_name:
					batchmesh.DistributeAllItemsToScenarios()
					batchmesh.RunMeshingScenario(Surf_Mesh_Scenario)
					outputUnits = utils.UnitSystem(length='meter')
					base.OutputFluent(os.path.join(output_mesh_dir, mesh_names[i]), format = "binary", write_solver_info = "on", mode = 'visible', unit_system = outputUnits)
					
			base.SetANSAdefaultsValues({'tolerance_mode':'middle'})	
	
	filenames = [name for name in os.listdir(gdir) if os.path.isfile(os.path.join(gdir, name))]
	for filename in filenames:
		if filename.endswith('.log'):
			try:
				if os.path.isfile(os.path.join(gdir, filename)):
					os.remove(os.path.join(gdir, filename))
					
			except OSError as oserr:
				print('OS error during deleting file:')
				print(filename)
				print('OS error: {0}'.format(oserr))
	

	

	message = '\n\n\n\n'\
	'############################################################################################################\n'\
	'############################################  SCRIPT COMPLETED  ############################################\n'\
	'############################################################################################################\n'\
	'\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'h')
	voidarea = False
	if fix_negative_vol_fill_void_cfdpp_partial == -1 or fix_negative_vol_fill_void_openfoam_partial == -1 or fix_negative_vol_fill_void_partial == -1 or fix_negative_vol_fill_void_fluent == -1:
		upper_frame('w')
		message = '\nVoid areas remain. Function failed in filling the void after negative volume deletion.\n'\
		'As a result, the boundaries of the void area will be put together under the name\ndefault-exterior (in mcfd.bc file) for the proper boundary condition setup.\n'\
		'OR...\nIf you have the time, go back and try to avoid the negative element. Most of the problems in \nmesh generation are related to the surface mesh strategy and/or quality.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('w')
		voidarea = True
		
	if negvol_cfdpp_total_final == 0 and negvol_cfdpp_partial_final == 1:
		upper_frame('w')
		message = '\nMesh is OK for CFD++ TOTAL volume calculation method but not for CFD++ PARTIAL.\nSetup CFD++ to run on total cell volume instead of cell component.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('w')
		if not voidarea:
			# Good Job
			quit_ansa(gdir, output_mesh_dir, log_file, name, 4)
		else:
			# Its up to you
			quit_ansa(gdir, output_mesh_dir, log_file, name, 5)
			
	if not 'LAYERS_MESH' in geom:
		if negvol_cfdpp_partial_layers == 1 and negvol_cfdpp_partial_final == 0:
			if not voidarea:
				# Great Success
				quit_ansa(gdir, output_mesh_dir, log_file, name, 1)
			else:
				# Its up to you
				quit_ansa(gdir, output_mesh_dir, log_file, name, 5)
				
		if negvol_cfdpp_partial_layers == 0 and negvol_cfdpp_partial_final == 0:
			if not voidarea:
				# Great Success Borat
				quit_ansa(gdir, output_mesh_dir, log_file, name, 3)
			else:
				# Its up to you
				quit_ansa(gdir, output_mesh_dir, log_file, name, 5)
	else:
		if negvol_cfdpp_partial_final == 0:
			if not voidarea:
				# Great Success
				quit_ansa(gdir, output_mesh_dir, log_file, name, 1)
			else:
				# Its up to you
				quit_ansa(gdir, output_mesh_dir, log_file, name, 5)
			
	if negvol_cfdpp_total_final == 1:
		# Mesh fail
		upper_frame('e')
		message = '\nMesh ended with negative volume for CFD++ TOTAL method.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('e')
		quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
	
	if negvol_fluent_final == 1:
		# Mesh fail
		upper_frame('e')
		message = '\nMesh ended with negative volume for FLUENT method.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('e')
		quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
		
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ END OF MAIN FUNCTION $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$		
	
	
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ START OF SUB FUNCTIONS $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#	$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$	

# This function projects the all red CONS onto the symmetry plane and delete the resultant small internal faces.
def auto_trim_on_symmetry_plane():
	base.All()
	group_objects = []
	max_vol = 0
	largest_group = None
	groups = base.IsolateConnectivityGroups(0, 0, 0)
	for group, entities in groups.items():
		b = base.BoundBox(entities)
		vol = (b[3] - b[0]) * (b[4] - b[1]) * (b[5] - b[2])
		group_obj = group_object(group, entities, vol)
		group_objects.append(group_obj)
		if vol > max_vol:
			max_vol = vol
			largest_group = group_obj
			
	group_objects.pop(group_objects.index(largest_group))
	
	wings_faces = []

	for g in group_objects:
		wings_faces.extend(g.entities)
	
	symmetry_face = None
	for f in largest_group.entities:
		bbox = base.BoundBox(f)
		if abs(bbox[1] - bbox[4]) < 0.5:
			symmetry_face = f
		
	red_cons = []
	cons = base.CollectEntities(constants.OPENFOAM, wings_faces, 'CONS')
	for c in cons:
		nr_of_pasted_cons = c.get_entity_values(constants.OPENFOAM, ['Number of Pasted Cons'])['Number of Pasted Cons']
		if nr_of_pasted_cons == 1:
			red_cons.append(c)
			
	if not symmetry_face:
		print('No symmetry face found. Abort.')
		return
		
	if not len(red_cons):
		print('No red CONS found to project. Abort.')
		return
	
	project = base.ConsProjectNormal(red_cons, symmetry_face, 0.0, True, True,False,True)

class group_object:
	def __init__(self, name, entities, vol):
		self.name = name
		self.entities = entities
		self.vol = vol
    
    

def hlpw_bcnames(bcnames, sw_filters, co_filters):
	# #######################################################################################################################################
	# Set PID function to merge and rename PIDs according to bc name list. This is specific to the HLPW convention work.
	
	# Create SET of bc names and add the respective PIDs according to the lists of filters
	pids = base.CollectEntities(constants.OPENFOAM, None, 'SHELL_PROPERTY')
	for idx, bcname in enumerate(bcnames):
		#print(bcname, idx)
		set = base.CreateEntity(constants.OPENFOAM, 'SET', {'Name' : bcname, 'SID' : idx+1000})	
		pids_filtered = []
		for pid in pids:
			if pid._name.startswith(sw_filters[idx]) and co_filters[idx] in pid._name:
				pids_filtered.append(pid)
				#print(pid._name)
		base.AddToSet(set, pids_filtered)
	# Make one PID for each SET
	_set2pid(bcnames)
		
	# #######################################################################################################################################

def _set2pid(bcnames):
	# Make one PID for each SET
	sets = base.CollectEntities(constants.OPENFOAM, None, 'SET')
	if not sets:
		message = 'No sets found'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')

	for set in sets:
		vals = base.GetEntityCardValues(constants.OPENFOAM, set, ('Name','SID'))
		set_name = vals['Name']
		set_id = vals['SID']
		
		if set_name in bcnames:
		
			shell_prop_ids = []
			shell_props = base.CollectEntities(constants.OPENFOAM, None, 'SHELL_PROPERTY')
			for shell_prop in shell_props:
				shell_prop_ids.append(shell_prop._id)
			
			solid_prop_ids = []
			solid_props = base.CollectEntities(constants.OPENFOAM, None, 'SOLID_PROPERTY')
			for solid_prop in solid_props:
				solid_prop_ids.append(solid_prop._id)
			
			if set_id in shell_prop_ids:
				conflicting_prop = base.GetEntity(constants.OPENFOAM, 'SHELL_PROPERTY', set_id)
				new_id = set_id + 10000000
				base.SetEntityCardValues(constants.OPENFOAM, conflicting_prop, {'PID':new_id})
				
			if set_id in solid_prop_ids:
				conflicting_prop = base.GetEntity(constants.OPENFOAM, 'SOLID_PROPERTY', set_id)
				new_id = set_id + 10000000
				base.SetEntityCardValues(constants.OPENFOAM, conflicting_prop, {'PID':new_id})
				
			prop = base.CreateEntity(constants.OPENFOAM, 'SHELL_PROPERTY', {'Name':set_name, 'PID':set_id})
			
			vals2 = base.GetEntityCardValues(constants.OPENFOAM, prop, ('PID', ))
			pid = vals2['PID']
			types = ['FACE', 'SHELL', 'SHELL_PROPERTY']
			faces = base.CollectEntities(constants.OPENFOAM, set, types, recursive = True)
			for face in faces:
				base.SetEntityCardValues(constants.OPENFOAM, face, {'PID':pid})
			
def Merge_PIDs_Same_Name():
	deck = constants.OPENFOAM
	
	pids = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
	pidnames = []
	for pid in pids:
		pidnames.append(pid._name)
	
	seen = {}
	duples = []
	for x in pidnames:
		if x not in seen:
			seen[x] = 1
		else:
			if seen[x] == 1:
				duples.append(x)
			seen[x] += 1
	
	if duples:
		message = 'Found duplicate PID names.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		for name in duples:
			message = name + '\n'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		for idx, pidname in enumerate(duples):
			set = base.CreateEntity(constants.OPENFOAM, 'SET', {'Name' : pidname, 'SID' : idx+1000})
			pids_filtered = []
			for pid in pids:
				if pidname in pid._name:
					pids_filtered.append(pid)
			base.AddToSet(set, pids_filtered)
	
		_set2pid(duples)	
		base.Compress('')
	else:
		message = '\n\nNo duplicate PID names found.\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	

def _fix_quality_volume(vol_calc_method, nodes_move_distance):

	# Negative volume 
	message = '\n\n  - Negative volume calculation method : ' + vol_calc_method + '\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.F11SolidsOptionsSet('negative volume', True, vol_calc_method, 0)
	
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Fix quality volume
	ansa.mesh.FixQualSolids(nodes_move_distance)
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	


def _fix_negvol_fill_void(vol_calc_method):

	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\nDelete negative volume and fill the void... First try.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		negative_elements_second_try = _delete_negvol_and_fill_the_void(negative_elements,vol_calc_method,'2')
		if negative_elements_second_try == 'voidremains':
			return -1
		if negative_elements_second_try != 0:
			message = '\nDelete negative volume and fill the void... Second try.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			negative_elements_third_try = _delete_negvol_and_fill_the_void(negative_elements_second_try,vol_calc_method,'3')
			if negative_elements_third_try == 'voidremains':
				return -1
			if negative_elements_third_try != 0:
				message = '\nDelete negative volume and fill the void... Third try.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				negative_elements_fourth_try = _delete_negvol_and_fill_the_void(negative_elements_third_try,vol_calc_method,'4')
				if negative_elements_fourth_try == 'voidremains':
					return -1
				if negative_elements_fourth_try != 0:
					message = '\nQuit trying to fix it. Check your mesh!'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					return 0
					
				else: return 1
				
			else: return 1
			
		else: return 1
		
	else: return 1



def _IntersectAll():

	deck = constants.OPENFOAM
	
	inter = checks.penetration.Intersections()
	res = inter.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	report = res[0]
	if report.issues:
		print(len(report.issues), ' intersections found')
#		report.method = 'Collapse'
#		report.method = 'Move Away'
		report.method = 'Intersect Entities'
#		report.maximum_movement = '50'
	
		report.try_fix()	
		

def _resetMacros():

	deck = constants.OPENFOAM
	
	check1 = 0
	check2 = 0

	ret = base.GetViewButton(('PERIMS','DOUBLE'))
	if (ret['PERIMS']) == 0:
		base.SetViewButton({'PERIMS':'on',})
		check1+=1
	if (ret['DOUBLE']) == 0:
		base.SetViewButton({'DOUBLE':'on',})
		check2+=1

	cons = base.CollectEntities(deck, None, 'CONS', filter_visible = True)
	if cons:
		ret = mesh.ReleaseMacros( cons, remesh_macros =  False, keep_mesh = False, delete_hot_points = True)
		#message = 'Macros>Release All...OK!'
		#print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		mesh.JoinMacros(cons, keep_mesh = False, auto_delete_hot_points = True)
		#message = 'Macros>Join All...OK!'
		#print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
		cons = base.CollectEntities(deck, None, 'CONS', filter_visible = True)
		if cons:
			ret = mesh.ReleaseMacros( cons, remesh_macros =  False, keep_mesh = False, delete_hot_points = True)
			#message = 'Macros>Release All...OK!'
			#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
		cons = base.CollectEntities(deck, None, 'CONS', filter_visible = True)
		if cons:
			mesh.InitPerimeters( cons, False, False, True)
			#message = 'Perimeters>Initialize...OK!'
			#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	grids = base.CollectEntities(deck, None, 'NODE', filter_visible = True)
	if grids:
		mesh.MoveGridsToOrigin(grids)
		#message = 'Grids>Origin...OK!'
		#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	base.DeleteVisibleHotPoints()
	#message = 'Hot Points>Delete...OK!'
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	if check1:
		base.SetViewButton({'PERIMS':'off',})
	if check2:
		base.SetViewButton({'DOUBLE':'off',})		

def _autotrim():

	deck = constants.OPENFOAM

	base.All()
	
	base.SetANSAdefaultsValues({'tolerance_mode':'extra_fine'})
	base.SetANSAdefaultsValues({'	ntolerance':0.003125})	
	base.SetANSAdefaultsValues({'ctolerance':0.0125})
	
	message = '\nIntersecting and fixing geometry... Please wait.\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Intersect
	_IntersectAll()
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	

	base.SetANSAdefaultsValues({'tolerance_mode':'draft'})		
	base.SetANSAdefaultsValues({'	ntolerance':0.2})	
	base.SetANSAdefaultsValues({'ctolerance':0.8})
	
	message = '\nGenerating STL mesh... Please wait.\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Generate STL mesh
	mesh.AspacingSTL(10, 10000, 0, 10)
	mesh.CreateStlMesh()
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	#base.All()
	#base.SaveAs('./AFTER_MESH.ansa')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Volume detection
	vols = mesh.VolumesDetect(return_volumes = True, whole_db = True)
	m.stop_buffering()
	ret_buffer_vol_detect = m.get_buffer()
	m.clear()
	#base.SaveAs('./AFTER_AUTODETECT.ansa')
	vols_dict = {}
	if vols:
		for vol in vols:
			volume = base.GetEntityCardValues(deck, vol, ['Volume'])['Volume']
			vols_dict[volume] = vol
	else:
		upper_frame('e')
		# Write internal messages to log file
		for i in ret_buffer_vol_detect:
			message = i + '\n'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
		message = '\nProblem in volume detection. Abort! Abort!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('e')
		# Quit ANSA
		quit_ansa(gdir, output_mesh_dir, log_file, name, 2)
		
	volumes_sorted = list(vols_dict.keys())
	volumes_sorted.sort()
#	print(volumes_sorted)
	base.All()
	base.Not(vols_dict[volumes_sorted[-1]])
    ###### LEX study only ###################
	#base.Not(vols_dict[volumes_sorted[-2]])
	#base.Not(vols_dict[volumes_sorted[-3]])
	#base.Not(vols_dict[volumes_sorted[-4]])
    #########################################
	#base.SaveAs('./teste.ansa')
	vis_faces = base.CollectEntities(deck, None, 'FACE', filter_visible = True)
	base.DeleteEntity(vis_faces)
	base.All()

	allVols = base.CollectEntities(deck, None, 'VOLUME')
	base.DeleteEntity(allVols)
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Compressing
	base.Compress('')
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	
	message = '\nErase STL mesh.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	mesh.EraseMesh()
	
	base.SetANSAdefaultsValues({'tolerance_mode':'middle'})		
	base.SetANSAdefaultsValues({'	ntolerance':0.05})
	base.SetANSAdefaultsValues({'ctolerance':0.2})
	
	message = '\nReseting Macros to fix any unchecked faces...\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Reseting Macros
	_resetMacros()
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	
	

def _check_geom(base_mesh, scons, tcons):

	deck = constants.OPENFOAM

	# Check and Fix Geometry
	allpshells = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
	options = ['CRACKS', 'OVERLAPS', 'NEEDLE FACES', 'COLLAPSED CONS', 'UNCHECKED FACES', 'SINGLE CONS', 'TRIPLE CONS']
	
	fix = [0, 0, 0, 0, 0, 0, 0]
	ret = base.CheckAndFixGeometry(allpshells, options, fix, True, True)
	if ret != None:
		for geom_warning in ret['remaining_errors']:
			message = '\nGeometry warning :  ' + geom_warning
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		message = '\nTrying to fix geometry applying Topo to the whole model...'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		base.Topo()
		message = '\nChecking geometry again.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		ret = base.CheckAndFixGeometry(allpshells, options, fix, True, True)
		if ret != None:
			for geom_warning in ret['remaining_errors']:
				message = '\nGeometry warning :  ' + geom_warning
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
			if not base_mesh:
				fix = [1, 1, 1, 1, 1, 1, 1]
			else:
				fix = [1, 1, 1, 1, 1, 1, 0]	
			if scons == 0 and tcons == 0:
				message = '\nTrying to fix geometry using auto fix... last try.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				ret = base.CheckAndFixGeometry(allpshells, options, fix, True, True)
				message = '\nChecking geometry again.'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				if ret != None:
					for geom_warning in ret['remaining_errors']:
						message = '\nGeometry warning :  ' + geom_warning
						print_message(os.path.join(gdir, log_file), message, 1, 'b')
						if geom_warning == 'Single Cons' and scons == 1:
							message = 'No problem in having Single Cons, UNLESS you do not expect to have them.'
							print_message(os.path.join(gdir, log_file), message, 1, 'b')
						elif geom_warning == 'Triple Cons' and tcons == 1:
							message = 'No problem in having Triple Cons, UNLESS you do not expect to have them.'
							print_message(os.path.join(gdir, log_file), message, 1, 'b')
						else:
							return True
				else:
					message = '\nSingle cons and triple cons allowed.'
			else:
				message ='\nGeometry fixed!'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
		else:
			message ='\nGeometry fixed!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
	else:
		message ='\nGeometry OK!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')

		
		
def _SetPidVolume(fluid_property_name):

	deck = constants.NASTRAN
	
	id = [10000]
	allvolumes = base.CollectEntities(deck, None, 'VOLUME')
	message = 'Number of existing volumes: ' + str(len(allvolumes)) + '\n\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	vals2 = {'PID':id[0]}
	for vol in allvolumes:
		base.SetEntityCardValues(deck, vol, vals2)
	
	newPsolid = base.GetEntity(deck, 'PSOLID', 10000)
	vals3 = {'Name':fluid_property_name}
	if newPsolid:
		base.SetEntityCardValues(deck, newPsolid, vals3)
	else:
		upper_frame('w')
		message = '\nNo PSOLID elements found.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		lower_frame('w')

		
		
def _fix_tria_on_corners():

	deck = constants.OPENFOAM
	
	message = '\n\nIdentify trias on corners and swap them.\n'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Check tria
	cornerTrias = checks.mesh.TriasOnCorner()
	res = cornerTrias.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	report = res[0]
	if report.issues:
		report.try_fix()
		message = '\nTria on corners fixed.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')


def _check_fix_Intersections():

	deck = constants.OPENFOAM
	message = '\n\nChecking for intersections...'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	inter = checks.penetration.Intersections()
	#print(dir(inter))
	res = inter.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	report = res[0]
	if report.issues:
		message = '\nFound ' + str(len(report.issues)) + ' intersections.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		report.method = 'Move Away'
		message = '\nTrying to auto fix off elements...'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		report.try_fix()
		message = '\nChecking for intersections again...'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		inter = checks.penetration.Intersections()
		res = inter.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
		report = res[0]
		if report.issues:
			#print(len(report.issues))
			upper_frame('w')
			for issue in report.issues:
				message = issue.description
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
			#message = '\nProblem! Open mesh and check for intersections.'
			message = '\nFound ' + str(len(report.issues)) + ' intersections.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('w')
		else:
			message = '\nAll intersections fixed. Good!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
	else:
		message = '\nNo intersections found. Good!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')


def _check_fix_Sharp():

	deck = constants.OPENFOAM

	surf_mesh_shells = base.CollectEntities(deck, None, 'SHELL', filter_visible=True)
	sharp_edge_angle = 160.0
	message = '\n\nChecking for sharp edges with angle above ' + str(sharp_edge_angle) + ' deg'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	ret = base.CheckSharpEdges(0, sharp_edge_angle)
	if ret:
		list1 = []
		for key in ret:
			if key == 'concave_errors': sharp_edges = ret[key]
			if key == 'convex_errors': sharp_edges = ret[key]
			if key == 'mixed_errors': sharp_edges = ret[key]
			for sharp_edge in sharp_edges:
				ent = base.GetEntity(deck, "SHELL", sharp_edge._id)
				pid = base.GetEntityCardValues(deck, ent, ['PID'])['PID']
				if key != 'convex_errors':
					list1.append(pid)
		pids_sharp_edge = list(set(list1))
	
		pshells = base.CollectEntities(deck, None, 'SHELL_PROPERTY')
		pid_name = []
		for pshell in pshells:
			pid = base.GetEntityCardValues(deck, pshell, ['PID'])['PID']
			pname = base.GetEntityCardValues(deck, pshell, ['Name'])['Name']
			for pid_sharp_edge in pids_sharp_edge:
				if pid_sharp_edge == pid:
					pid_name.append(pname)
				
		sharp_edge_pname = ' '.join(map(str, pid_name))
	
	sharp = checks.mesh.SharpEdges()
	#print(dir(sharp))
	# Define settings of the check
	sharp.angle = sharp_edge_angle
	#sharp.exclude_edges = 0
	#sharp.sharp_edges_type = 'Concave'
	res = sharp.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	report = res[0]
	#print(dir(report))
	sharp_num = 0
	if report.issues:
		for issue in report.issues:
			if issue.description == 'Concave edges' or issue.description == 'Mixed edges':
				message = '\nFound ' + issue.description + ' with angle above ' + str(sharp_edge_angle) + ' deg in PIDs : ' + str(sharp_edge_pname)
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				report.expand_level = 5
				report.reshape_violating = True
				message = '\nTrying to auto fix off elements...'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				while sharp_num <= 1:
					sharp_num += 1
					report.try_fix()
					if sharp_num == 1:
						break

		message = '\nChecking for sharp edges again...'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		sharp = checks.mesh.SharpEdges()
		sharp.angle = sharp_edge_angle
		res = sharp.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
		report = res[0]
		sharp_count = 0
		if report.issues:
			for issue in report.issues:
				title = issue.description
				if issue.description == 'Concave edges' or issue.description == 'Mixed edges':
					message = '\n' + str(len(report.issues)) + ' ' + issue.description + ' remains'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					sharp_count += 1
		if sharp_count == 0:
			message = '\nAll sharp edges fixed. Good!'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		else:
			upper_frame('w')
			message = '\nOpen the surface mesh manually and check for sharp edges.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			lower_frame('w')
	else:
		message = '\nNo sharp edges found. Good!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')



def _check_fix_Quality():

	deck = constants.OPENFOAM
	message = '\n\nChecking surface mesh quality...'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFrozen shells/macros meshed with Map mesh will be excluded.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Hide all Map mesh macros before running check mesh quality
	faces = base.CollectEntities(deck, None, 'FACE')
	faces_with_map = []
	foundmap = 0
	for face in faces:
		ret = base.GetEntityCardValues(deck, face, ['Meshed With'])
		if ret['Meshed With'] == '4 SIDED':
			faces_with_map.append(face)
			foundmap = 1
	if foundmap == 1:
		base.Not(faces_with_map) 
		
	# Change skewness default value only for the anisotropic mesh issues that might happen due to the zone cut lack of robustness
	_InactiveShellCriteria()
	skew_shell = 0.95
	skew_shell_type = 'FLUENT'
	message = '\n  - Maximum shell skewness for tria elements : ' + str(skew_shell) + '  ' + str(skew_shell_type) 
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.F11ShellsOptionsSet('skewness', True, skew_shell_type, skew_shell)
	
	warping_shell = 10
	warping_shell_type = 'IDEAS'
	message = '\n  - Maximum shell warping angle : ' + str(warping_shell) + '  ' + str(warping_shell_type) 
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.F11ShellsOptionsSet('warping', True, warping_shell_type, warping_shell)
	
	#maxang_tria = 0.9
	#maxang_tria_type = 'FLUENT'
	#message = '\n  - Maximum angle ratio between edges for tria elements : ' + str(maxang_tria) + '  ' + maxang_tria_type 
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11ShellsOptionsSet('max angle trias', True, maxang_tria_type, maxang_tria)
	#
	#maxang_quad = 0.7
	#maxang_quad_type = 'FLUENT'
	#message = '\n  - Maximum angle ratio between edges for quad elements : ' + str(maxang_quad) + '  ' + maxang_quad_type 
	#print_message(os.path.join(gdir, log_file), message, 1, 'b')
	#base.F11ShellsOptionsSet('max angle quads', True, maxang_quad_type, maxang_quad)
	
	qual = checks.mesh.MeshQuality()
	res = qual.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	report = res[0]
	if len(report.issues)!=0:
		for issue in report.issues:
			title = issue.description
			if title.startswith('skewness') or title.startswith('warping'):
				message = '\n' + title
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				message = '\nTrying to improve skewness/warping of the selected off elements...'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				ansa.mesh.ReconstructViolatingShells(3)
				message = '\nChecking for bad skewness/warping again...'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				qual = checks.mesh.MeshQuality()
				res = qual.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
				report = res[0]
				skew_count = 0
				for issue in report.issues:
					title = issue.description
					if title.startswith('skewness') or title.startswith('warping'):
						skew_count += 1
				if skew_count == 0:
					message = '\nAll bad skewness/warping have been solved'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#if len(report.issues)!=0:
				#	for issue in report.issues:
				#		title = issue.description
				#		if title.startswith('skewness'):
				#			message = '\nStill violating skewness are found.\n'
				#			print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#			message = '\n' + title
				#			print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#			message = '\nTrying to auto fix off elements... 2nd pass.'
				#			print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#			ansa.mesh.ReconstructViolatingShells(3)
				#			qual = checks.mesh.MeshQuality()
				#			res = qual.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
				#			report = res[0]
				#			skew_count == 0
				#			for issue in report.issues:
				#				title = issue.description
				#				if title.startswith('skewness'):
				#					skew_count += 1
				#			if skew_count == 0:
				#				message = '\nAll bad skewness have been solved'
				#				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#			if len(report.issues)!=0:
				#				for issue in report.issues:
				#					title = issue.description
				#					if title.startswith('skewness'):
				#						message = '\nStill violating skewness are found.'
				#						print_message(os.path.join(gdir, log_file), message, 1, 'b')
				#						message = '\n' + title
				#						print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	# Back to default value
	skew_shell = 0.7
	skew_shell_type = 'FLUENT'
	base.F11ShellsOptionsSet('skewness', True, skew_shell_type, skew_shell)
	
	
	# Bring to visible hidden Map mesh
	base.And(faces_with_map)									
		
def _check_neg_vols_and_auto_fix(vol_calc_method):
	
	deck = constants.OPENFOAM
	
	negvol = checks.mesh.NegativeVolume()
	negvol.calculation_method = vol_calc_method
	message = '\nCalculation method: ' + vol_calc_method
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	res = negvol.execute(exec_mode = Check.EXEC_ON_MODEL, report = Check.REPORT_NONE)
	report = res[0]
	if report.issues:
		for issue in report.issues:
			title = issue.description
			message = '\n' + title
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			message = '\nAttempting to fix negative elements.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			ents = issue.entities
			report.try_fix()	
			neg_vols = ents
			
			message = '\nChecking for negative volume elements again.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			negvol = checks.mesh.NegativeVolume()
			negvol.calculation_method = vol_calc_method
			res = negvol.execute(exec_mode = Check.EXEC_ON_MODEL, report = Check.REPORT_NONE)
			report = res[0]
			if report.issues:
				for issue in report.issues:
					title = issue.description
					message = '\nUnfixed negative volume remains. Not good.\n'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					message = '\n' + title
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					return(1)
			else:
				message = '\nFixed negative volume. Good!!!\n'
				print_message(os.path.join(gdir, log_file), message, 1, 'b')
				return(0)
	else:
		message = '\nNo negative volume. Great Success!!!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		return(0)
		
	
def _checkNegative(vol_calc_method):
	
	neg = checks.mesh.NegativeVolume()
	neg.calculation_method = vol_calc_method
	message = '\nCalculation method: ' + vol_calc_method
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	res = neg.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	report = res[0]
	if report.issues:
		neg = []
		for issue in report.issues:
			title = issue.description
			message = '\n' + title
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			neg.extend(issue.entities)
		return(neg)
	else:
		message = '\nNo negative volume. Great Success... Ufa!'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		return 0


def _delete_negvol_and_fill_the_void(negative_elements,vol_calc_method,n_neighbors):

	deck = constants.OPENFOAM
	
	message = '\nIsolating negative elements plus ' + str(n_neighbors) + ' neighboring zones...'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.Or(negative_elements)
	base.Neighb(n_neighbors)
	vis_solids = base.CollectEntities(deck, None, 'SOLID', filter_visible = True)
	# Bring an extra neighbor so we have the surronding elements to check for void areas after solid elements deletion.
	base.Neighb('1')
	message = '\nDeleting ' + str(len(vis_solids)) + ' solid elements...'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	base.DeleteEntity(vis_solids)
	# Do not base.All here! Memory issue when function checks.mesh.VoidAreas is applyed.
	#base.All()
	voidareas = _checkVoidAreas()
	voidareas1 = 0
	if voidareas == 1:
		voidareas1 = _checkVoidAreas()
		if voidareas1 == 1:
			message = '\nVoid areas remain. Not good. Inspect mesh manually for void areas.'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
	message = '\nFinal check for negative elements.'
	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	negative_elements = _checkNegative(vol_calc_method)
	if negative_elements != 0:
		message = '\nUnfixed negative volume remains. Not good.\n'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		return negative_elements
	else:
		if voidareas1 == 1:
			return 'voidremains'
		else:
			return 0

		
def _checkVoidAreas():	
	# Get internal messages
	m = utils.Messenger()
	m.start_buffering()
	# Check void area
	voidareas = checks.mesh.VoidAreas()
	res = voidareas.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	m.stop_buffering()
	ret_buffer = m.get_buffer()
	# Write internal messages to log file
	for i in ret_buffer:
		message = '\n' + i + '\n'
		print_message(os.path.join(gdir, log_file), message, 0, 'b')
		if 'Volume detection may be erroneous!' in i:
			message = 'This should be no problema. Chill out.'
			print_message(os.path.join(gdir, log_file), message, 0, 'b')
	m.clear()
	
	report = res[0]
	if report.issues:
		neg = []
		for issue in report.issues:
			title = issue.description
			message = '\n' + title
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
			message = '\nFixing void areas...'
			print_message(os.path.join(gdir, log_file), message, 1, 'b')
		report.try_fix()
		return 1
	else:
		message = '\nNo void areas found.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		return 0

		
def _InactiveShellCriteria():
	inactive_shell_criteria = ['aspect ratio', 'skewness', 'warping', 'min height', 'squish', 'jacobian', 'min length', 'max length', 'min angle quads', 'max angle quads', 'min angle trias', 'max angle trias', 'mesh distortion', 'growth ratio', 'h-ratio', 'thickness to length']
	for criterion in inactive_shell_criteria:
		ret = base.F11ShellsOptionsGet(criterion)
		base.F11ShellsOptionsSet(criterion, False, str(ret['calculation']), ret['value'])	
	
def _InactiveSolidCriteria():
	inactive_solid_criteria = ['aspect ratio', 'skewness', 'warping', 'squish', 'jacobian', 'min length', 'max length', 'min angle pentas', 'max angle pentas', 'min angle hexas', 'max angle hexas', 'non orthogonality', 'growth ratio', 'negative volume', 'left handed', 'min height', 'h-ratio', 'determinant', 'layers quality', 'face tetquality', 'min volume']
	for criterion in inactive_solid_criteria:
		ret = base.F11SolidsOptionsGet(criterion)
		base.F11SolidsOptionsSet(criterion, False, str(ret['calculation']), ret['value'])

#	###########################################################################################
#	############################ Sub Function: rotation_matrix ################################
# 	This function Calculates Rotation Matrix given euler angles.
#	###########################################################################################
def rotation_matrix(thetax, thetay, thetaz):
     
    Rx = np.array([[1,               0,               0             ],
                   [0,               mt.cos(thetax), -mt.sin(thetax)],
                   [0,               mt.sin(thetax),  mt.cos(thetax)]])

    Ry = np.array([[mt.cos(thetay),  0,               mt.sin(thetay)],
                   [0,               1,               0             ],
                   [-mt.sin(thetay), 0,               mt.cos(thetay)]])

    Rz = np.array([[mt.cos(thetaz), -mt.sin(thetaz),  0             ],
                   [mt.sin(thetaz),  mt.cos(thetaz),  0             ],
                   [0,               0,               1             ]])

    R = np.dot(Rz, np.dot(Ry, Rx))
    return R
	




#	###########################################################################################
#	############### Sub Functions: Boundary Layer Mesh Parameters Calculation #################
#	###########################################################################################
# 	This session ...
#	###########################################################################################
def first_layer_height(rey, lref, ypls):
	# Estimation of first layer height based on a reference length for a turbulent boundary 
	# layer over a flat plate. The local skin friction coefficient used to derive this equation 
	# is a 1/7 power law with experimental calibration given by cfx = 0.0576*Reyx**(-0.2). 
	# Reference: Schlichting, Hermann (1979). Boundary-Layer Theory.
	h0 = (2.0/0.0592)**0.5*rey**(-0.9)*ypls*lref
	# meter to millimiter
	h0 = h0*1000.0
	return h0

def total_layers_height(rey, lref):
	# Estimation of boundary layer height based on a reference length for a turbulent boundary 
	# layer over a flat plate. 
	# Reference: Schlichting, Hermann (1979). Boundary-Layer Theory.
	H = 0.37*rey**(-0.2)*lref

	# meter to millimiter
	H = H*1000.0
	return H

def number_of_layers(h0, H, r):
	n = mt.log(H/h0*(r-1.0)+1.0)/mt.log(r)
	return int(round(n))

def growth_factor_layers(h0, H, n):
	# Solving the geometric summation equation for the common ratio "r" (Layers Growth Factor) 
	# using Newtons method given the first layer height (h0), the total layers height (H) and 
	# the number of layers (n).
	def f(r, h0, H, n):
		return h0*((r**(n+1.0)-1.0)/(r-1.0))-H

	def df(r, h0, n):
		return h0*((n*r**(n+1.0)-(n+1.0)*r**n-1.0)/(r-1.0)**2.0)

	def dr(f, r, h0, H, n):
		return abs(0-f(r, h0, H, n))

	def newtons_method(f, df, e, r0, h0, H, n):
		delta = dr(f, r0, h0, H, n)
		while delta > e:
			r0 = r0 - f(r0, h0, H, n)/df(r0, h0, n)
			delta = dr(f, r0, h0, H, n)
		return r0
	
	n = n - 1
	r0 = 1.1
	return newtons_method(f, df, 1e-5, r0, h0, H, n)
	#wlay_n = wlay_n + 1


#	###########################################################################################
#	########################### Sub Function: Set Layers Scenario #############################
#	###########################################################################################
# 	This session ...
#	###########################################################################################
def Set_Layers_Scenario(wlay_y0,wlay_r,blay_n):
	# Here the Layer Areas for the Layers Mesh session will be created so the values calculated in the 
	# Boundary Layer Mesh Parameters be applied.
	# Layers Areas settings (filter name, first height, growth ratio, growth type, zero thickness, layers property name, filter match by:, filter match by:, match name, filter match by:)
	#	filter name          string     The name of the filter and mesh parameters of the created area.
	#	first height         float      First layer height value of the mesh parameters of created area.
	#	growth ratio         float     	Growth rate of layers.
	#	growth type  		 string     Determines whether first layer height value is expressed as an absolute value or as a factor (aspect) of the local element length. Accepted values "aspect" or "absolute".
	#	zero thickness       boolean    Will grow layers for both sides of zero thickness walls.
	#	layers property name string     Property name of generated solid elements.
	#	filter match by:	 string		Name, Id, Comment, All, etc.
	#	filter match by:	 string		contains, doesnt contain, startswith, endswith, etc.
	#	match name		 	 string		The property name (or any part of it) of a PID to be matched
	#	filter match by:	 string		all or any

	row1  = ['SMOOTH', 			wlay_y0, wlay_r, 'absolute', False, "fluid_layers_smooth", 			'All',  'contains',		'_', 		'all']
	row2  = ['NO-SMOOTH', 		wlay_y0, wlay_r, 'absolute', False, "fluid_layers_no-smooth", 		'Name', 'contains',		'_upp', 	'any']
	row3  = ['NO-SMOOTH', 		wlay_y0, wlay_r, 'absolute', False, "fluid_layers_no-smooth", 		'Name', 'contains',		'_low', 	'any']
	row4  = ['NO-SMOOTH', 		wlay_y0, wlay_r, 'absolute', False, "fluid_layers_no-smooth", 		'Name', 'contains',		'_ted', 	'any']
	row5  = ['NO-SMOOTH', 		wlay_y0, wlay_r, 'absolute', False, "fluid_layers_no-smooth", 		'Name', 'contains',		'_cap', 	'any']
	row6  = ['SPINNER', 		wlay_y0, wlay_r, 'absolute', False, 'fluid_layers_spinner',			'Name', 'starts with',	'x.spn', 	'all']
	row7  = ['FUSELAGE', 		wlay_y0, wlay_r, 'absolute', False, 'fluid_layers_fuselage',		'Name', 'starts with',	'b', 		'any']
	row8  = ['FUSELAGE', 		wlay_y0, wlay_r, 'absolute', False, 'fluid_layers_fuselage',		'Name', 'starts with',	'f', 		'any']
	
	arg = [row1, row2, row3, row4, row5, row6, row7, row8]
	
	# Get Layer session and create the specified Layer Areas. Skip it if Layer Areas already exist.
	layers_areas = base.CollectEntities(deck, None, 'BATCH_MESH_LAYERS_AREA')
	if len(layers_areas) == 0:
		layers_ses = []
		layerScenarios = base.CollectEntities(deck, None, 'BATCH_MESH_LAYERS_SCENARIO')
		for lscen in layerScenarios:
			if lscen._name == 'Layers_Mesh_Session':
				layerSessions = batchmesh.GetSessionsFromMeshingScenario(lscen)
				for sess in layerSessions:
					if sess._name == 'Layers_Mesh_Session':
						for i in range(len(arg)):
							if i == 0:
								area = batchmesh.GetNewLayersArea(sess, name=arg[i][0], first_height=arg[i][1], growth_factor=arg[i][2], first_height_method=arg[i][3], zero_thickness=arg[i][4], layers_prop_name=arg[i][5])
								batchmesh.AddFilterToSession(arg[i][6], arg[i][7], arg[i][8], area, match=arg[i][9], filter_name=arg[i][0])
							else:
								if arg[i][0] != arg[i - 1][0]:
									area = batchmesh.GetNewLayersArea(sess, name=arg[i][0], first_height=arg[i][1], first_height_method=arg[i][3], growth_factor=arg[i][2], zero_thickness=arg[i][4], layers_prop_name=arg[i][5])
									batchmesh.AddFilterToSession(arg[i][6], arg[i][7], arg[i][8], area, match=arg[i][9], filter_name=arg[i][0])
								else:
									batchmesh.AddFilterToSession(arg[i][6], arg[i][7], arg[i][8], area, match=arg[i][9], filter_name=arg[i][0])
		batchmesh.DistributeAllItemsToScenarios()
	else:
		print("")
		print("Layer Areas already exist")
		print("")
		
		
	# Saving layers session mesh parameters
	

	lparam = 'Layers_Mesh_Parameters.ansa_mpar'
	batchSessions = base.CollectEntities(deck, None, 'BATCH_MESH_LAYERS_SESSION')
	for batchSession in batchSessions:
		if batchSession._name == 'Layers_Mesh_Session':
			ret_val = batchmesh.SaveSessionMeshParams(batchSession, './' + str(lparam))

	lparam_new = lparam + '_new.ansa_mpar'
	f = open(lparam_new, 'w')
	f.close()

	# ANSA keywords for the layer parameters
	keywords = ['layers_first_height', 'layers_growth_factor', 'Requested_layers']
	
	# Layer parameters values
	parameters = [wlay_y0, wlay_r, blay_n]
	
	# Loop over file lparam searching for the keywords and replacing their values. New file lparam_new will be created
	for line in fileinput.input(str(lparam)):
		for keyword, parameter in zip(keywords, parameters):
			#This REGEX pattern will match for every keyword string followed by an equal sign which is followed by any number, 
			#no matter how many spaces (or no space) exist between them.
			pattern_regex = '\s*'+str(keyword)+'\s*=\s*[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?'
			replace_regex = '  ' +str(keyword)+'        = '+str(parameter)
			line = re.sub(pattern_regex, replace_regex, line.rstrip())
		f = open(lparam_new, 'a')
		f.write(line + "\n")
		f.close()

	# Reading the new parameters from file lparam_new
	batchSessions = base.CollectEntities(deck, None, 'BATCH_MESH_LAYERS_SESSION')
	for batchSession in batchSessions:
		if batchSession._name == 'Layers_Mesh_Session':
			ret_val = batchmesh.ReadSessionMeshParams(batchSession, './' + str(lparam_new))


#	###########################################################################################
#	################## Sub Function: Check and Fix Nodes Away From Symmetry ###################
# 	This function will fix all the nodes away from the symmetry plane
#	###########################################################################################
def checkSymmetry():
	symCheck = checks.mesh.Symmetry_Plane()
	res = symCheck.execute(exec_mode = Check.EXEC_ON_VIS, report = Check.REPORT_NONE)
	report = res[0]
	if report.issues:
		message = '\nFound nodes lying away from symmetry.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		report.try_fix()
		message = 'Nodes fixed.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	else:
		message = '\nAll symmetry nodes lie on symmetry plane.'
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	return


#	###########################################################################################
# 	Quit ANSA and delete default log files
#	###########################################################################################
def quit_ansa(gdir, output_mesh_dir, log_file, mesh_name, ascii_art):
	# Delete default log files.
	if gdir:
		filenames = os.listdir(gdir)
		for filename in filenames:
			if filename.endswith('.log'):
				try:
					os.remove(os.path.join(gdir, filename))
				except OSError as oserr:
					message = '\nOS error during deleting default log files:\n'
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
					message = 'OS error: {0}'.format(oserr)
					print_message(os.path.join(gdir, log_file), message, 1, 'b')
	# Print log file name
	#if log_file:
	#	message = '\n\n\nLog file : ' + log_file + '\n'
	#	print_message(os.path.join(gdir, log_file), message, 1, 'b')
	
	# Print Great Success
	if ascii_art == 1:
		CallGreatSuccess()
	# Print Mesh Fail
	if ascii_art == 2:
		CallMeshFail()
	# Print Borat
	if ascii_art == 3:
		CallGreatSuccessBorat()
	# Print Good Job
	if ascii_art == 4:
		CallGoodJob()
	# Print Its Up to You
	if ascii_art == 5:
		CallItsUpToYou()
	
	# Change the name meshlog file
	shutil.move(os.path.join(gdir, log_file), os.path.join(gdir, mesh_name + '.ansa.meshlog'))
	
	# Copy mesh log file to output mesh dir
	if output_mesh_dir:
		shutil.copy2(os.path.join(gdir, mesh_name + '.ansa.meshlog'), os.path.join(output_mesh_dir, mesh_name + '.ansa.meshlog'))
	
	# Quit ANSA		
	session.Quit()
	
#	###########################################################################################


#	###########################################################################################
# 	Write logfile and print messages on terminal
# 	###########################################################################################
def print_message(pathfile, message, msgterminal, msgtype):
	# Print message on terminal
	if msgterminal == 1:
		if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
			if msgtype == 'h':
				print(bcolors.HEADER + message + bcolors.ENDC)
			elif msgtype == 's':
				print(bcolors.SUCCESS + message + bcolors.ENDC)
			elif msgtype == 'gj':
				print(bcolors.GOOD_JOB + message + bcolors.ENDC)
			elif msgtype == 'gs':
				print(bcolors.GREAT_SUCCESS + message + bcolors.ENDC)
			elif msgtype == 'u2u':
				print(bcolors.UP_TO_YOU + message + bcolors.ENDC)
			elif msgtype == 'w':
				print(bcolors.WARNING + message + bcolors.ENDC)
			elif msgtype == 'e':
				print(bcolors.ERROR + message + bcolors.ENDC)
			elif msgtype == 'f':
				print(bcolors.FAIL + message + bcolors.ENDC)
			elif msgtype == 'mf':
				print(bcolors.MISERLY_FAIL + message + bcolors.ENDC)
			elif msgtype == 'b':
				print(message)
		else:
			print(message)
	# Write message to log file
	try:
		with open(pathfile, 'a') as f:
			f.write(str(message))
	except OSError as oserr:
		print('OS error during saving or opening file:')
		print(pathfile)
		print('OS error: {0}'.format(oserr))		
# 	###########################################################################################


# 	###########################################################################################
# 	Message frames 
# 	###########################################################################################
def upper_frame(msgtype):
	if msgtype == 'e': messa_name = '      ERROR       '
	if msgtype == 'w': messa_name = '     WARNING      '
	if msgtype == 'f': messa_name = '      FAIL        '
	if msgtype == 's': messa_name = '     SUCCESS      '
	message = '\n\n'\
	'############################################################################################################\n'\
	'#############################################' + messa_name + '#############################################\n'\
	'############################################################################################################'
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, msgtype)
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
def lower_frame(msgtype):
	message = '\n'\
	'############################################################################################################\n'\
	'############################################################################################################\n'\
	'############################################################################################################\n'
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, msgtype)
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
# 	###########################################################################################

# 	############################################################################################################
#   ASCII art its up to you
#	############################################################################################################
def CallItsUpToYou():
	message = '\n\n'\
	"8888888 888                                              888                                           \n"\
	"  888   888      88                                      888                                           \n"\
	"  888   888     888                                      888                                           \n"\
	"  888   888888 888  .d8888b       888  888 88888b.       888888 .d88b.       888  888  .d88b.  888  888\n"\
	"  888   888         88K           888  888 888 '88b      888   d88''88b      888  888 d88''88b 888  888\n"\
	"  888   888         'Y8888b.      888  888 888  888      888   888  888      888  888 888  888 888  888\n"\
	"  888   Y88b.            X88      Y88b 888 888 d88P      Y88b. Y88..88P      Y88b 888 Y88..88P Y88b 888\n"\
	"8888888  'Y888       88888P'       'Y88888 88888P'        'Y888 'Y88P'        'Y88888  'Y88P'   'Y88888\n"\
	"                                           888                                    888                  \n"\
	"                                           888                               Y8b d88P                  \n"\
	"                                           888                                'Y88P'                   \n"
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, 'u2u')
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
# 	############################################################################################################

# 	############################################################################################################
#   ASCII art good job
#	############################################################################################################
def CallGoodJob():
	message = '\n\n'\
	"                                                .o8           o8o            .o8                    \n"\
	"                                               '888           `^'           '888                    \n"\
	"            .oooooooo  .ooooo.   .ooooo.   .oooo888          oooo  .ooooo.   888oooo.               \n"\
	"           888' `88b  d88' `88b d88' `88b d88' `888          `888 d88' `88b  d88' `88b              \n"\
	"           888   888  888   888 888   888 888   888           888 888   888  888   888              \n"\
	"           `88bod8P'  888   888 888   888 888   888           888 888   888  888   888              \n"\
	"           `8oooooo.  `Y8bod8P´ `Y8bod8P´ `Y8bod88P'          888 `Y8bod8P´  `Y8bod8P´              \n"\
	"           d'     YD                                          888                                   \n"\
	"           'Y88888P'                                      .o. 88P                                   \n"\
	"                                                          `Y888P                                    \n"
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, 'gj')
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
# 	############################################################################################################

# 	############################################################################################################
#   ASCII art great success
#	############################################################################################################
def CallGreatSuccess():
	message = '\n\n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@       @.      @       @     @@@       @@@@       @  @@. .@      .N      @       Z:      N       @@@    \n'\
	'@@@  @@@  @. @@@  @  @@@. @  @  N@@  @@,  @@@@   @@  @  @@. .@  @@  .N  @@  @  @@@  Z@  I@  N@  8@  @@@    \n'\
	'@@@  @@@  @. @@@  @  @@@,,@  @7  @@@@@@:  @@@@@  I+++@  @@. .@  @@.,,N  @@.,@  @@@.,$@   @++N@   @++@@@    \n'\
	'@@@       @.      @    @@@@  @@  @@@@@@,  @@@@@:  @@@@  @@. .@  @@@@@N  @@@@@     @@@@@   @@@@@   @@@@@    \n'\
	'@@@?.     @.     ~@    @@@@  @@  @@@@@@,  @@@@@@.  @@@  @@. .@  @@@@@N  @@@@@     @@@@@@   @@@@@   @@@@    \n'\
	'@@@@@@@@  @. @  @@@  @@8 .@  @@   @@@@@,  @@@@  @.  @@  @@. .@  @@   N  @@  @  @@@  I:  @  O@   @  @@@@    \n'\
	'@@@  @@@  @. @=  @@  @@8  @       @@@@@,  @@@@  @@  O@  @@. .@  @@   N  @@  @  @@@  I:  @I  @   @:  @@@    \n'\
	'@@@       @. @@  O@       @  @@O  @@@@@,  @@@@       @      .@       N      @       I:      D       @@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, 'gs')
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
# 	############################################################################################################


# 	############################################################################################################
#   ASCII art mesh fail
#	############################################################################################################

def CallMeshFail():
	message = '\n\n'\
	'          @@@@@@@@@@   @@@@@@@@   @@@@@@   @@@  @@@        @@@@@@@@   @@@@@@   @@@  @@@         \n'\
	'          @@@@@@@@@@@  @@@@@@@@  @@@@@@@   @@@  @@@        @@@@@@@@  @@@@@@@@  @@@  @@@         \n'\
	'          @@! @@! @@!  @@!       !@@       @@!  @@@        @@!       @@!  @@@  @@!  @@!         \n'\
	'          !@! !@! !@!  !@!       !@!       !@!  @!@        !@!       !@!  @!@  !@!  !@!         \n'\
	'          @!! !!@ @!@  @!!!:!    !!@@!!    @!@!@!@!        @!!!:!    @!@!@!@!  !!@  @!!         \n'\
	'          !@!   ! !@!  !!!!!:     !!@!!!   !!!@!!!!        !!!!!:    !!!@!!!!  !!!  !!!         \n'\
	'          !!:     !!:  !!:            !:!  !!:  !!!        !!:       !!:  !!!  !!:  !!:         \n'\
	'          :!:     :!:  :!:           !:!   :!:  !:!        :!:       :!:  !:!  :!:   :!:        \n'\
	'          :::     ::    :: ::::  :::: ::   ::   :::         ::       ::   :::   ::   :: ::::    \n'\
	'           :      :    : :: ::   :: : :     :   : :         :         :   : :  :    : :: : :    \n'
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":                
		print_message(os.path.join(gdir, log_file), message, 1, 'mf')                                  
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
# 	############################################################################################################


# 	############################################################################################################
#   ASCII art great success Borat
#	############################################################################################################
def CallGreatSuccessBorat():
	message = '\n\n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@O7, .   .N@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.                 =@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ .                    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ .                        @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ .                           @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@                                  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@..                                 .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.                                   .@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@          I@@@@@. ?$@=.@@@,           7@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@+        @@@@@@@@@@@@@@@@@@@          @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@        @@@@@@@@@@@@@@@@@@@@         @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@       @@@@@@@@@@@@@@@@@@@@        :@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.     @@@@@@@@@@@@@@@@@@@@.       @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,     @@@@@@@@@@@@@@@@@@@@@.    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    @@@,8@@@@@@@@@@@@@@~ .     @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ @  @@.N.    @@@@@@.   Z@8. . @.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.@@,@@@O.@.@..@@@@  ZN ..@@@,@@ @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@D@@@.@,@=@@@@N.@.@O ,@@@Z@@D@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ @@I@@@@@@ @@@@@@.Z@@N@@@@@@@.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.@@@@@@@@@@@.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.@@@@@@@@@@@@@@@. @@@@@@@+@@$@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,@@@@@@@@@8@@@@,@ @@@@@@.@.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@:?...D@@ .. . @@@.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ @@                 =@:@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.@....... .. .. . ..8  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@I@ @@@+N@@@@@=8 @+@=@N@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@.@@@@@@ 8@@@@ .D:@@= @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@,@@@@@@N@+.~.?@@@ @.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  @@@@@@@@@@@@@@.@. @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@N.@.@@@@@@@@@@@@@@@@@@@@@@@.@?@+@@@@@@@@@@ N.@  @@@@@@@@@@@@@@@@@@@@@@@@@@ N@.@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@ @@@.@@@@@@@@@@@@@@@@@@@@@@.@@@OI@@@@@@@  @.8Z . @@@@@@@@@@@@@@@@@@@@@@@@O@@@@.@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@ @@@@O@@@@@@@@@@@@@@@@@@@@.   @@@ @ ...    @@@     D@@@@@@@@@@@@@@@@@@@@@.@@@@.@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@ @@@@.@@@@@@@@@@@@@@@@@N.       @@@@D:?$@@@@~.     8I@@@@@@@@@@@@@@@@@@@@@@@@:@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@ @@@N@@@@@@@@@@@@@@@, @@.        ,@@@@@@@          @O O@@@@@@@@@@@@@@@@.@@@@D@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@ @@@@@@@@@@@@..:@@@.            : .           @@N@$ @@@@@@@@@@@@@@Z@@@.@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@,@@@@@Z.+@7@@@@@@@@+ $@@D@@@.         8$@@@@.          @@@@@@@@.,@@@@@@@@@ 7 @@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@O@@@@@@@@@@ @@@@ .@@@ @@@@@@@@.       ~@@@@@.           @@@@@@@@@.@@: .@@@7.@@@@@@@@@ @@@@@@@@    \n'\
	'@@@@@@@@+@@@,@D .@@ZN @@@@@@@ @@@@@@@@@.         @@@             @@@@@@@@@@.@@@@@@D @@@,~@@$7@@@ @@@@@@    \n'\
	'@@@@@@@O@@@@@@@@@@@ @@@@@@@@D@@@@@@@@@@@          @@.           .@@@@@@@@@@@7@@@@@@:@@@@@@@@@@@@.@@@@@@    \n'\
	'@@@@@@D7@@@,@@@@@@@ @@@@@@@@@@@@@@@@@@@@          @@            @@@D@@@@@@@@@@@@@@@ +@@@@@@$.@@@@8@@@@@    \n'\
	'@@@@@@ @@@@@@@@@@.@@@@@@@@@8@@@@@@@@@@@@          @@.           @@@~@@@@@@@@@ @@@@@ O@ @@@@@@@@@@@@@@@@    \n'\
	'@@@@@@.@@@@@@@@@@@ @Z@@@@@@@I.@@@@@@@@@@@        @@@I           @@Z@@@@@@@@.@@@@@@@@@O:@@@@@@@@@@.@@@@@    \n'\
	'@@@@@@+@@@@@@@@.@@,@,@@@@@@@@@@.@@@@@@@@@        @@@@.         ,@@.@@@@@@ +@@@@@@@@@,@@@.@@@@@@@@,@@@@@    \n'\
	'@@@@@@N+@@@@@@@@ .@,@@@@@@@@@@.@@@@:@@@@@N      Z@@@@@         @@@@@@@@@@@@@@@@@@@@@@.@@@@@@@@@@@.@@@@@    \n'\
	'@@@@@@@  ~@ N@@N@@~@@@@@@@@@@Z@@@@@=@@@@@@      @@@@@@@.       @@8@@@@@@@@@@.@@@@@@@@@@.@$O, N.8.@@@@@@    \n'\
	'@@@@@@@@  .@@@D@@@N@@@@@@@@~@@@@@@@@@@@@@@,     @@@@@@@        @@@@@@@@@@@@@@~@@@@@@@@ @@N@@@@.  @@@@@@    \n'\
	'@@@@@@@N.  . .  .  @@@@@@@@.@@@@@@@@:@@@@@@     @@@@@@@@      I@@@@@@@@@=@@@@.@@@@@@@. .. ...    @@@@@@    \n'\
	'@@@@@@@.   .=  @@ @$@@.@@@@@ @@@@@@@+@@@@@@+    @@@@@@@@.     @@@@@@@@@@@@N@@.@@@@=@@.+@@@,      @@@@@@    \n'\
	'@@@@@@@    @@@@@.?@?@@+,@@@@ @@@@@@@@.@@@@@@    @@@@@@@@N     @@@@@@@@@@@@@@.@@@@.@@8@@.@@@@@,.  @@@@@@    '
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
		
	message = '\n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@       @.      @       @     @@@       @@@@       @  @@. .@      .N      @       Z:      N       @@@    \n'\
	'@@@  @@@  @. @@@  @  @@@. @  @  N@@  @@,  @@@@   @@  @  @@. .@  @@  .N  @@  @  @@@  Z@  I@  N@  8@  @@@    \n'\
	'@@@  @@@  @. @@@  @  @@@,,@  @7  @@@@@@:  @@@@@  I+++@  @@. .@  @@.,,N  @@.,@  @@@.,$@   @++N@   @++@@@    \n'\
	'@@@       @.      @    @@@@  @@  @@@@@@,  @@@@@:  @@@@  @@. .@  @@@@@N  @@@@@     @@@@@   @@@@@   @@@@@    \n'\
	'@@@?.     @.     ~@    @@@@  @@  @@@@@@,  @@@@@@.  @@@  @@. .@  @@@@@N  @@@@@     @@@@@@   @@@@@   @@@@    \n'\
	'@@@@@@@@  @. @  @@@  @@8 .@  @@   @@@@@,  @@@@  @.  @@  @@. .@  @@   N  @@  @  @@@  I:  @  O@   @  @@@@    \n'\
	'@@@  @@@  @. @=  @@  @@8  @       @@@@@,  @@@@  @@  O@  @@. .@  @@   N  @@  @  @@@  I:  @I  @   @:  @@@    \n'\
	'@@@       @. @@  O@       @  @@O  @@@@@,  @@@@       @      .@       N      @       I:      D       @@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'\
	'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@    \n'
	if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
		print_message(os.path.join(gdir, log_file), message, 1, 'gs')
	else:
		print_message(os.path.join(gdir, log_file), message, 1, 'b')
# 	############################################################################################################
