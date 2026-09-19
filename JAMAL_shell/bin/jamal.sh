#!/bin/bash

############################################################################
################################ FUNCTIONS #################################

source ${JAMAL_ROOT}/lib/utils.sh

############################################################################
############################## MAIN PROGRAM ################################

env_to_array cnfg_param AERODYNAMIC_CONFIGURATION
env_to_array rudd_param RUDDER
env_to_array elev_param ELEVON
env_to_array aile_param AILERON
env_to_array flap_param FLAP
env_to_array fani_param FANINLET
env_to_array fano_param FANOULET
env_to_array core_param COREEXHA
env_to_array prop_param PROPELLER
env_to_array iter_param KNITERS
env_to_array probe_param PROBES
# env_to_array alcl_param ALPHA_CLS
# env_to_array becy_param BETA_CYS
# env_to_array mave_param MACH_VEL
env_to_array grid_param GRID

  #***************************** START PROCESS *******************************

  # Check matrix parameters and print error messages.
  # ------------------------------------------------
  # R?: Check if polar status is set to run.

env_to_array alpha_cl ALPHA_CLS
env_to_array alcl_mode alpha_cls_mode

env_to_array beta_cy BETA_CYS
env_to_array becy_mode beta_cys_mode

env_to_array mach_vel MACH_VEL
env_to_array mave_mode mach_vel_mode

env_to_array rehp_param REY_ALT
env_to_array rehp_mode rey_alt_mode

env_to_array mach_sweep mach_sweep
# env_to_array alpha_cl_sweep alpha_cl_sweep
# env_to_array beta_cy_sweep beta_cy_sweep
env_to_array cnfg cnfg

env_to_array isad ISAD

    if [[ $mave_mode == "VEL" ]] && [[ $rehp_mode == "ALT" ]]; then
      s_speed=$(sound_speed ${rehp_param[0]} ${isad})
      for i in "${!mach_vel[@]}"; do
        mach_vel[$i]=$(awk "BEGIN {print ${mach_vel[$i]}/$s_speed}")
      done
    fi


    multi_mesh_files=false
    aoa_grid=false
    if [[ ${#grid_param[@]} != 1 ]]; then
      for i in "${!grid_param[@]}"; do
        if is_not_number "${grid_param[$i]}"; then
          if [[ $i = 0 ]]; then
            multi_mesh_files=true
            if [[ ${grid_param[$i],,} = *aoa ]]; then
              aoa_grid=true
            fi
          fi
        fi
      done
    fi

env_to_array polr POL
env_to_array acrt ACRT
env_to_array nref REF
env_to_array nset SET
env_to_array turb TURB
env_to_array solv SOLVER
env_to_array stgy START
env_to_array wtim WTIME
env_to_array ncpu CPU

env_to_array jamal_mode jamal_mode
env_to_array line_number line_number

env_to_array matrix matrix


# exit 0
    
if [[ ${grid_param[0]} == "run_ansa_batch"* ]]; then
  
  if [ ! -f "01-GRIDS/ANSA/${grid_param[0]}" ]; then
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! POLAR-$polr mesh config file ${grid_param[0]} was not found in directory 01-GRIDS/ANSA." | fold -sw 80  
    failed_mesh_count=$(awk "BEGIN {printf \"%d\", $failed_mesh_count + 1}")
    if [[ $failed_mesh_count == 1 ]]; then
      printf "%s\n" "ABORTED! POLAR-$polr mesh config file ${grid_param[0]} was not found in directory 01-GRIDS/ANSA." > warning
    else
      printf "%s\n" "ABORTED! POLAR-$polr mesh config file ${grid_param[0]} was not found in directory 01-GRIDS/ANSA." >> warning
    fi

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi
  
  cd 01-GRIDS/ANSA 
  cp ${grid_param[0]} run_ansa.sh
  cnfg=""

  trans_param_count=1
  morph_param_count=1
  geom_count=1
  geom_str=true
  param_str=false
  translate_param=false
  morphing_param=false
  trans_mode=0
  morph_mode=0
  cnfg_trans=""
  cnfg_morph=""
  
  # temporary holders for the actual values
  declare -a trans_vals
  declare -a morph_vals
  
  for i in "${!cnfg_param[@]}"; do
    if [[ ${cnfg_param[$i]} == "*t" ]] || [[ ${cnfg_param[$i]} == "*m" ]]; then 
      geom_str=false
      param_str=true
    fi
    cad_extension=(".ansa" ".CATPart" "iges" ".igs")
  
    if $geom_str; then
    if [[ "${cnfg_param[$i]}" == *.ansa ]] || [[ "${cnfg_param[$i]}" == *.CATPart ]] || [[ "${cnfg_param[$i]}" == *.iges ]] || [[ "${cnfg_param[$i]}" == *.igs ]]; then
      sed -i "s/%geom_$geom_count%/${cnfg_param[$i]}/g" run_ansa.sh
    else
      sed -i "s/%geom_$geom_count%/${cnfg_param[$i]}.ansa/g" run_ansa.sh
    fi
      geom_count=$((geom_count+1))
      if [[ $i == 0 ]]; then 
      cad_ext_found=false
      for cad_ext in "${cad_extension[@]}"; do
        if [[ "${cnfg_param[$i]}" == *"$cad_ext" ]]; then
          cnfg="${cnfg_param[$i]%$cad_ext}"
          cad_ext_found=true
          break   # stop after first match (optional)
        fi
      done
      if ! $cad_ext_found ; then
        cnfg="${cnfg_param[$i]}"
      fi
      
      cad_ext_found=false

      elif [[ ${cnfg_param[$i]} != *FARFIELD* ]]; then
        for cad_ext in "${cad_extension[@]}"; do
          if [[ "${cnfg_param[$i]}" == *"$cad_ext" ]]; then
            cnfg+="_${cnfg_param[$i]%$cad_ext}"
            cad_ext_found=true
            break   # stop after first match (optional)
          fi
        done
        if ! $cad_ext_found ; then
          cnfg+="_${cnfg_param[$i]}"
        fi
      fi
    fi
  
    if $param_str; then
      case "${cnfg_param[$i]}" in
        "*t")
          translate_param=true
          morphing_param=false
          trans_mode=1
          trans_vals=()    # reset the translate array
          ;;
        "*m")
          morphing_param=true
          translate_param=false
          morph_mode=1
          morph_vals=()    # reset the morph array
          ;;
        *)
          if $translate_param; then
            # collect and replace
            trans_vals+=( "${cnfg_param[$i]}" )
            sed -i "s/%trans_param_$trans_param_count%/${cnfg_param[$i]}/g" run_ansa.sh
            trans_param_count=$((trans_param_count+1))
          elif $morphing_param; then
            morph_vals+=( "${cnfg_param[$i]}" )
            sed -i "s/%morph_param_$morph_param_count%/${cnfg_param[$i]}/g" run_ansa.sh
            morph_param_count=$((morph_param_count+1))
          fi
          ;;
      esac
    fi
  done
  
  # strip off trailing zeros
  trim_trailing_zeros() {
    local arr=( "$@" )
    while (( ${#arr[@]} > 0 )) && [[ ${arr[-1]} == 0 ]]; do
      unset 'arr[-1]'
    done
    # print space‑separated, not newline
    echo "${arr[@]}"
  }
  
  # build the final cnfg_trans
  if (( trans_mode )); then
    cnfg_trans="_t"
    # direct array assignment from the function’s space‑separated output
    trimmed=( $(trim_trailing_zeros "${trans_vals[@]}") )
    for v in "${trimmed[@]}"; do
      cnfg_trans+="_${v}"
    done
  fi
  
  # same for cnfg_morph
  if (( morph_mode )); then
    cnfg_morph="_m"
    trimmed=( $(trim_trailing_zeros "${morph_vals[@]}") )
    for v in "${trimmed[@]}"; do
      cnfg_morph+="_${v}"
    done
  fi

  for i in "${!rudd_param[@]}"; do
    #Removed flap and elevon to avoid appending mcs to the name file. We need to fix this logic with *t and *m that conflicts with this part.
    #flap_param[$i]="-"
    #elev_param[$i]="-"
    if [[ ${rudd_param[$i]} != "-" ]] || [[ ${elev_param[$i]} != "-" ]] || [[ ${aile_param[$i]} != "-" ]] || [[ ${flap_param[$i]} != "-" ]]; then
      cnfg_morph+="_mcs"
      if [[ $morph_mode == 0 ]]; then
        morph_mode=2
      else
        morph_mode=3
      fi
      break
    fi
  done

  sed -i s/%trans_mode%/"$trans_mode"/g run_ansa.sh
  sed -i s/%morph_mode%/"$morph_mode"/g run_ansa.sh
  
  if (( $(echo "$geom_count <= 5" | bc -l) )); then
    for i in $(seq $geom_count 5); do
      sed -i s/%geom_$i%/""/g run_ansa.sh
    done
  fi
  
  if (( $(echo "$trans_param_count <= 12" | bc -l) )); then
    if [[ $trans_mode == 1 ]]; then
      for i in $(seq $trans_param_count 12); do
        sed -i s/%trans_param_$i%/"0"/g run_ansa.sh
        #cnfg_trans=${cnfg_trans}_0
      done
    else
      for i in $(seq 1 12); do
        sed -i s/%trans_param_$i%/"0"/g run_ansa.sh
      done
    fi
  fi

  # 1) Flatten in desired order
  raw_params=(
    "${rudd_param[@]}"
    "${elev_param[@]}"
    "${aile_param[@]}"
    "${flap_param[@]}"
  )
  
  # 2) Filter out all '-' entries
  filtered_params=()
  for v in "${raw_params[@]}"; do
    [[ "$v" == "-" ]] && continue
    filtered_params+=("$v")
  done
  
  # 3) Determine start index
  if (( morph_mode == 1 )) || (( morph_mode == 3 )); then
    start=$morph_param_count
  else
    start=1
  fi
  
  # 4) Loop from start…12, using filtered_params or zero-fill
  max=12
  for (( i = start; i <= max; i++ )); do
    idx=$(( i - start ))    # zero-based index into filtered_params
  
    if (( idx < ${#filtered_params[@]} )); then
      val=${filtered_params[idx]}
      sed -i "s/%morph_param_${i}%/${val}/g" run_ansa.sh
    else
      val=0
      sed -i "s/%morph_param_${i}%/${val}/g" run_ansa.sh
      val="-"
    fi
    
    if [[ $val != "-" ]]; then
      cnfg_morph+="_${val}"
    fi

  done

  cnfg=${cnfg}${cnfg_trans}${cnfg_morph}

  #echo $cnfg
  #exit 1
  
  ############################# Start mesh generation #################################
  mesh_output_dir="../Fluent_Meters_${cnfg}"
  mesh_already_exist=false
  if [ ! -d $mesh_output_dir ]; then
    echo ""
    echo ""
    printf "\e${YELLOW}%4s %s\n\e${NC}" "                            MESH GENERATION POLAR " "$polr"
    printf "\e${YELLOW}%4s\n\e${NC}" "                            =========================="
    printf "\e${YELLOW}%4s %s\n\e${NC}" "Mesh name: ${cnfg}"

    ./run_ansa.sh

  else  
    mesh_already_exist=true
    printf "\n\e${YELLOW}%1s\n\e${NC}" "WARNING! Output mesh directory Fluent_Meters_${cnfg} for POLAR‑$polr already exists. If the file mesh exist, no new mesh will be generated. The case will be submitted with the existing mesh." | fold -sw 80
    failed_mesh_count=$(awk "BEGIN {printf \"%d\", $failed_mesh_count + 1}")
    if [[ $failed_mesh_count == 1 ]]; then
      printf "%s\n" "WARNING! POLAR-$polr Output mesh directory Fluent_Meters_${cnfg} already exists. If the file mesh exist, no new mesh will be generated. The case will be submitted with the existing mesh." > ../../warning
    else
      printf "%s\n" "WARNING! POLAR-$polr Output mesh directory Fluent_Meters_${cnfg} already exists. If the file mesh exist, no new mesh will be generated. The case will be submitted with the existing mesh." >> ../../warning
    fi
  fi

  grid_param[0]=${cnfg}
  cd ../../

  mesh_output_file="01-GRIDS/Fluent_Meters_${cnfg}/${cnfg}.msh.h5"
  if [ ! -f $mesh_output_file ]; then
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Output mesh file ${cnfg}.msh.h5 for POLAR‑$polr was not found. Mesh generation may have failed." | fold -sw 80
    failed_mesh_count=$(awk "BEGIN {printf \"%d\", $failed_mesh_count + 1}")
    if [[ $failed_mesh_count == 1 ]]; then
      printf "%s\n" "ABORTED! POLAR-$polr Output mesh file ${cnfg}.msh.h5 was not found. Mesh generation may have failed." > warning
    else
      printf "%s\n" "ABORTED! POLAR-$polr Output mesh file ${cnfg}.msh.h5 was not found. Mesh generation may have failed." >> warning
    fi

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi

  meshlog_file="01-GRIDS/Fluent_Meters_${cnfg}/${cnfg}.ansa.meshlog"
  if [ ! -f $meshlog_file ]; then
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Meshlog file ${cnfg}.ansa.meshlog for POLAR‑$polr was not found in directory Fluent_Meters_${cnfg}." | fold -sw 80
    failed_mesh_count=$(awk "BEGIN {printf \"%d\", $failed_mesh_count + 1}")
    if [[ $failed_mesh_count == 1 ]]; then
      printf "%s\n" "ABORTED! POLAR-$polr Meshlog file ${cnfg}.ansa.meshlog was not found in directory Fluent_Meters_${cnfg}." > warning
    else
      printf "%s\n" "ABORTED! POLAR-$polr Meshlog file ${cnfg}.ansa.meshlog was not found in directory Fluent_Meters_${cnfg}." >> warning
    fi

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi

  start_pattern_1="Running volume mesh: Volume_Mesh_Scenario"
  start_pattern_2="Final check neg vol auto fix"

  #if sed -n "/$start_pattern_1/,\$p" "$meshlog_file" | grep -q "1 volumes meshed successfully"; then
  #Commented due to new situation where you have more then one volume meshes
  if sed -n "/$start_pattern_1/,\$p" "$meshlog_file" | grep -q "volumes meshed successfully"; then
    if ! $mesh_already_exist; then
      printf "\n\e${YELLOW}%1s\n\e${NC}" "Volume mesh for POLAR‑$polr generated successfully. Mesh: ${cnfg}" | fold -sw 80
    else
      printf "\n\e${YELLOW}%1s\n\e${NC}" "Existing mesh for POLAR‑$polr detected. Volume mesh is good to go. Mesh: ${cnfg}" | fold -sw 80
    fi
  else
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Volume mesh generation for POLAR-$polr failed. Mesh: ${cnfg}" | fold -sw 80
    failed_mesh_count=$(awk "BEGIN {printf \"%d\", $failed_mesh_count + 1}")
    if [[ $failed_mesh_count == 1 ]]; then
      printf "%s\n" "ABORTED! POLAR-$polr Volume mesh generation failed. Mesh: ${cnfg}" > warning
    else
      printf "%s\n" "ABORTED! POLAR-$polr Volume mesh generation failed. Mesh ${cnfg}" >> warning
    fi

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi
  if sed -n "/$start_pattern_2/,\$p" "$meshlog_file" | grep -q "No negative volume. Great Success!!!"; then
    if ! $mesh_already_exist; then
      printf "\n\e${YELLOW}%1s\n\e${NC}" "Final mesh for POLAR‑$polr generated successfully. Mesh: ${cnfg}" | fold -sw 80
    else
      printf "\n\e${YELLOW}%1s\n\e${NC}" "Existing mesh for POLAR‑$polr detected. Final mesh is good to go. Mesh: ${cnfg}" | fold -sw 80
    fi
  elif sed -n "/$start_pattern_2/,\$p" "$meshlog_file" | grep -q "Fixed negative volume. Good!!!"; then
    if ! $mesh_already_exist; then
      printf "\n\e${YELLOW}%1s\n\e${NC}" "Final mesh for POLAR‑$polr generated successfully. Mesh: ${cnfg}" | fold -sw 80
    else
      printf "\n\e${YELLOW}%1s\n\e${NC}" "Existing mesh for POLAR‑$polr detected. Final mesh is good to go. Mesh: ${cnfg}" | fold -sw 80
    fi
  else
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Mesh generation for POLAR‑$polr failed. Negative volumes detected. Mesh: ${cnfg}" | fold -sw 80
    failed_mesh_count=$(awk "BEGIN {printf \"%d\", $failed_mesh_count + 1}")
    if [[ $failed_mesh_count == 1 ]]; then
      printf "%s\n" "ABORTED! POLAR-$polr Mesh generation failed. Negative volumes detected. Mesh: ${cnfg}" > warning
    else
      printf "%s\n" "ABORTED! POLAR-$polr Mesh generation failed. Negative volumes detected. Mesh: ${cnfg}" >> warning
    fi

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi
fi

if [[ ${grid_param[0]} != "run_ansa_batch"* ]] && [[ ${#cnfg_param[@]} == 1 ]] && ! $multi_mesh_files && [[ ${grid_param[0]} != "POLAR-"* ]]; then
  meshlog_file="01-GRIDS/Fluent_Meters_${grid_param[0]}/${grid_param[0]}.ansa.meshlog" 
  if [ ! -f $meshlog_file ]; then
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Meshlog file ${grid_param[0]}.ansa.meshlog for POLAR‑$polr was not found in directory Fluent_Meters_${grid_param[0]}." | fold -sw 80

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi
fi

if [[ ${grid_param[0]} != "run_ansa_batch"* ]] && [[ ${#cnfg_param[@]} == 1 ]] && [ -f $meshlog_file ] && ! $multi_mesh_filesi && [[ ${grid_param[0]} != "POLAR-"* ]]; then
  start_pattern_1="Running volume mesh: Volume_Mesh_Scenario"
  start_pattern_2="Final check neg vol auto fix"

  #if sed -n "/$start_pattern_1/,\$p" "$meshlog_file" | grep -q "1 volumes failed to be meshed"; then
  #Commented due to new situation where you have more then one volume meshes
  if sed -n "/$start_pattern_1/,\$p" "$meshlog_file" | grep -q "volumes failed to be meshed"; then
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Volume mesh for POLAR-$polr is not good. Check if the volume mesh was successfully generated. Mesh: ${grid_param[0]}" | fold -sw 80

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi
  if sed -n "/$start_pattern_2/,\$p" "$meshlog_file" | grep -q "Unfixed negative volume remains. Not good."; then
    printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Final mesh for POLAR‑$polr is not good. Check for negative volume. Mesh: ${grid_param[0]}" | fold -sw 80

    line_number=$(awk "BEGIN {print $line_number + 1}")
    continue
  fi
fi

  



if [[ $nref == 0* ]]; then
  nref=$(printf "%03d" $((10#$nref)))
else
  nref=$(printf "%03d" $nref)
fi
if [[ $nset == 0* ]]; then
  nset=$(printf "%03d" $((10#$nset)))
else
  nset=$(printf "%03d" $nset)
fi
#if [[ $nhpc == 0*     ]]; then
#  nhpc=$(printf "%03d" $((10#$nhpc)))
#else
#  nhpc=$(printf "%03d" $nhpc)
#fi


# Read and check SET file parameters and print error messages.
# -----------------------------------------------------------
# Exit if the specified SET file does not exist.
if [ ! -f 00-SUPPORT/SET-"$nset" ]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter SET: File 00-SUPPORT/SET-$nset does not exist" | fold -sw 80
  exit 1
fi
# Create a dictionary of the SET file data.
declare -A dict_set
key_set=()
value_set=()
while IFS= read -r line; do
  if [[ $line == *"="* ]]; then
    line=$(echo "$line" | tr -d ';')
    key_set+=(${line%%=*})
    value_set+=(${line#*=})
  fi
done < "00-SUPPORT/SET-$nset"

for i in "${!key_set[@]}"; do
  dict_set[${key_set[$i]}]=${value_set[$i]}
done

ratio_update=${dict_set["ITER_UPDATE_OVER_ITERS_RATIO"]}
ratio_slope=${dict_set["ITER_SLOPE_OVER_ITERS_RATIO"]}
ratio_start=${dict_set["ITER_START_OVER_ITERS_RATIO"]}
ratio_next=${dict_set["ITER_NEXT_CASE_OVER_ITERS_RATIO"]}
cl_tol=${dict_set["DELTA_CL_TOL"]}
cy_tol=${dict_set["DELTA_CY_TOL"]}
da_slp=${dict_set["DELTA_ALPHA_DEG_SLOPE"]}
db_slp=${dict_set["DELTA_BETA_DEG_SLOPE"]}
da_max=${dict_set["DELTA_ANGLE_DEG_MAX"]}

iter_update=$(awk "BEGIN {printf \"%d\", $ratio_update*${iter_param[0]}*1000}")
iter_slope=$(awk "BEGIN {printf \"%d\", $ratio_slope*${iter_param[0]}*1000}")
iter_start=$(awk "BEGIN {printf \"%d\", $ratio_start*${iter_param[0]}*1000}")
iter_next=$(awk "BEGIN {printf \"%d\", $ratio_next*${iter_param[0]}*1000}")




# Read and check REF file parameters and print error messages.
# -----------------------------------------------------------
# Exit if the specified REF file does not exist.
if [ ! -f 00-SUPPORT/REF-"$nref" ]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter REF: File 00-SUPPORT/REF-$nref does not exist" | fold -sw 80
  exit 1
fi
# Create a dictionary of the REF file data.
declare -A dict
while IFS=: read -r key values_str; do
  key=${key// /}
  values=$(echo "$values_str" | tr -cd '[:print:][:cntrl:]\n')
  dict[$key]=${values[@]}
  # Error messages.
  IFS=" " read -r -a arr <<< "$values"
  for i in "${arr[@]}"; do
    if is_not_number "$i"; then
      printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter REF: Variable $key in the REF file REF-$nref is not a number." | fold -sw 80
      exit 1
    fi
    if [[ $key == "SREF" ]] || [[ $key == "CREF" ]] || [[ $key == "BREF" ]]; then
      if is_not_float_pos "$i"; then
        printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter REF: Variable $key in the REF file REF-$nref must be positive." | fold -sw 80
        exit 1
      fi
    fi
  done
done < "00-SUPPORT/REF-$nref"
# Creation of lists from each dictionary key values for each aircraft component in REF file.
IFS=" " read -r -a acrt_REF <<< "${dict["ACRT"]}" # Aircraft number.
IFS=" " read -r -a sref_REF <<< "${dict["SREF"]}" # Reference area  [m2].
IFS=" " read -r -a cref_REF <<< "${dict["CREF"]}" # Reference chord [m].
IFS=" " read -r -a bref_REF <<< "${dict["BREF"]}" # Reference span  [m].
IFS=" " read -r -a xref_REF <<< "${dict["XREF"]}" # Moment reference point X [m].
IFS=" " read -r -a yref_REF <<< "${dict["YREF"]}" # Moment reference point Y [m].
IFS=" " read -r -a zref_REF <<< "${dict["ZREF"]}" # Moment reference point Z [m].
IFS=" " read -r -a rudd_REF <<< "${dict["RUDD"]}" # Rudder number.
IFS=" " read -r -a x0hr_REF <<< "${dict["X0HR"]}" # Rudder hinge point X [m].
IFS=" " read -r -a y0hr_REF <<< "${dict["Y0HR"]}" # Rudder hinge point Y [m].
IFS=" " read -r -a z0hr_REF <<< "${dict["Z0HR"]}" # Rudder hinge point Z [m].
IFS=" " read -r -a dxhr_REF <<< "${dict["DXHR"]}" # Rudder hinge line vector component dx.
IFS=" " read -r -a dyhr_REF <<< "${dict["DYHR"]}" # Rudder hinge line vector component dy.
IFS=" " read -r -a dzhr_REF <<< "${dict["DZHR"]}" # Rudder hinge line vector component dz.
IFS=" " read -r -a elev_REF <<< "${dict["ELEV"]}" # Elevon number.
IFS=" " read -r -a x0he_REF <<< "${dict["X0HE"]}" # Elevon hinge point X [m].
IFS=" " read -r -a y0he_REF <<< "${dict["Y0HE"]}" # Elevon hinge point Y [m].
IFS=" " read -r -a z0he_REF <<< "${dict["Z0HE"]}" # Elevon hinge point Z [m].
IFS=" " read -r -a dxhe_REF <<< "${dict["DXHE"]}" # Elevon hinge line vector component dx.
IFS=" " read -r -a dyhe_REF <<< "${dict["DYHE"]}" # Elevon hinge line vector component dy.
IFS=" " read -r -a dzhe_REF <<< "${dict["DZHE"]}" # Elevon hinge line vector component dz.
IFS=" " read -r -a aile_REF <<< "${dict["AILE"]}" # Aileron number.
IFS=" " read -r -a x0ha_REF <<< "${dict["X0HA"]}" # Aileron hinge point X [m].
IFS=" " read -r -a y0ha_REF <<< "${dict["Y0HA"]}" # Aileron hinge point Y [m].
IFS=" " read -r -a z0ha_REF <<< "${dict["Z0HA"]}" # Aileron hinge point Z [m].
IFS=" " read -r -a dxha_REF <<< "${dict["DXHA"]}" # Aileron hinge line vector component dx.
IFS=" " read -r -a dyha_REF <<< "${dict["DYHA"]}" # Aileron hinge line vector component dy.
IFS=" " read -r -a dzha_REF <<< "${dict["DZHA"]}" # Aileron hinge line vector component dz.
IFS=" " read -r -a flap_REF <<< "${dict["FLAP"]}" # Flap number.
IFS=" " read -r -a x0hf_REF <<< "${dict["X0HF"]}" # Flap hinge point X [m].
IFS=" " read -r -a y0hf_REF <<< "${dict["Y0HF"]}" # Flap hinge point Y [m].
IFS=" " read -r -a z0hf_REF <<< "${dict["Z0HF"]}" # Flap hinge point Z [m].
IFS=" " read -r -a dxhf_REF <<< "${dict["DXHF"]}" # Flap hinge line vector component dx.
IFS=" " read -r -a dyhf_REF <<< "${dict["DYHF"]}" # Flap hinge line vector component dy.
IFS=" " read -r -a dzhf_REF <<< "${dict["DZHF"]}" # Flap hinge line vector component dz.
IFS=" " read -r -a prop_REF <<< "${dict["PROP"]}" # Propeller number.
IFS=" " read -r -a nbld_REF <<< "${dict["NBLD"]}" # Number of blades.
IFS=" " read -r -a diam_REF <<< "${dict["DIAM"]}" # Disk diameter [m].
IFS=" " read -r -a chor_REF <<< "${dict["CHOR"]}" # Blade chord [m].
IFS=" " read -r -a xhub_REF <<< "${dict["XHUB"]}" # Hub center point X [m].
IFS=" " read -r -a yhub_REF <<< "${dict["YHUB"]}" # Hub center point Y [m].
IFS=" " read -r -a zhub_REF <<< "${dict["ZHUB"]}" # Hub center point Z [m].
IFS=" " read -r -a xtil_REF <<< "${dict["XTIL"]}" # Tilt angle about +x axis [deg].
IFS=" " read -r -a ytil_REF <<< "${dict["YTIL"]}" # Tilt angle about +y axis [deg].
IFS=" " read -r -a ztil_REF <<< "${dict["ZTIL"]}" # Tilt angle about +z axis [deg].

if [[ ${#rudd_param[@]} != ${#rudd_REF[@]} ]]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter RUDDER: Number of inputs must match the number of rudders in the REF file REF-$nref." "RUDDER: $(param_descrip "RUDDER")" | fold -sw 80
  exit 1
fi
if [[ ${#elev_param[@]} != ${#elev_REF[@]} ]]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter ELEVON: Number of inputs must match the number of elevons in the REF file REF-$nref." "ELEVON: $(param_descrip "ELEVON")" | fold -sw 80
  exit 1
fi
if [[ ${#aile_param[@]} != ${#aile_REF[@]} ]]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter AILERON: Number of inputs must match the number of ailerons in the REF file REF-$nref." "AILERON: $(param_descrip "AILERON")" | fold -sw 80
  exit 1
fi
if [[ ${#flap_param[@]} != ${#flap_REF[@]} ]]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter FLAP: Number of inputs must match the number of flaps in the REF file REF-$nref." "FLAP: $(param_descrip "FLAP")" | fold -sw 80
  exit 1
fi
if (( $(echo "${#prop_param[@]} != ${#prop_REF[@]}*2" | bc -l) )); then
#if [[ ${#prop_param[@]} != ${#prop_REF[@]}+2 ]]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter PROPELLER: Number of inputs must match the number of propellers in the REF file REF-$nref." "PROPELLER: $(param_descrip "PROPELLER")" | fold -sw 80
  exit 1
fi

# Aircraft reference dimensions.
sref=${sref_REF[0]}
cref=${cref_REF[0]}
bref=${bref_REF[0]}
xref=${xref_REF[0]}
yref=${yref_REF[0]}
zref=${zref_REF[0]}

# For plane interpolation properties
inlet_plane_fan_1=false
inlet_plane_fan_2=false
exit_plane_fan_out_1=false
exit_plane_fan_out_2=false
exit_plane_core_out_1=false
exit_plane_core_out_2=false


# Create RUN and GRID directories, symbolic links, check grid files, etc.
# ----------------------------------------------------------------------
# Create a directory with the polar number if it does not exist.
mkdir -p "02-RUNS/POLAR-$polr"
# Change working directory to polar dir.
cd 02-RUNS/POLAR-$polr

# Check if mesh will be generated or use an existing one.
# In case grid file is provided, check solver type grid existence.
if [[ ${#grid_param[@]} == 1 ]] || $multi_mesh_files; then
  if [[ ${grid_param[0]} == "POLAR"* ]]; then
    start_from_polar_case=true
    polar_case=$(printf "%s" $(echo ${grid_param[0]}))
    if [[ $solv == "FLUENT" ]]; then
      polar_case_dir="../$polar_case"
      polar_case_filename="${polar_case#*/}"
      cas_link="${polar_case#*/}.cas.h5"
      dat_link="${polar_case#*/}.dat.h5"
      force_link="FORCE_${polar_case#*/}.out"
      moment_link="MOMENT_${polar_case#*/}.out"
      polar_dir=${polar_case%/*}

      # Check if case and dat files exist.
      ext1=""
      ext2=""
      [ -e ../$polar_case.cas.h5 ] && ext1="cas.h5"
      [ -e ../$polar_case.dat.h5 ] && ext2="dat.h5"
      # Exit if file extension is not found.
      if [[ $ext1 == "" ]] || [[ $ext2 == "" ]]; then
        printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Polar case to be used as starting case is not found $polar_case" | fold -sw 80
        #exit 1
      fi
      # Check if force and moment output files exist.
      force_file=false
      moment_file=false
      [ -e ../$polar_dir/$force_link ] && force_file=true
      [ -e ../$polar_dir/$moment_link ] && moment_file=true
      # Exit if force or moment file is not found.
      if ! $force_file || ! $moment_file; then
        printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Polar case FORCE and/or MOMENT output file is not found $polar_case" | fold -sw 80
        #exit 1
      fi

      # Remove all symbolic links if they exist.
      find -type l -delete

      # Create the symbolic links for the grid and meshlog files from the grid directory.
      ln -sf ../$polar_dir/$cas_link $cas_link
      ln -sf ../$polar_dir/$dat_link $dat_link
      ln -sf ../$polar_dir/$force_link $force_link
      ln -sf ../$polar_dir/$moment_link $moment_link
      ln -sf ../$polar_dir/meshlog meshlog

    elif [[ $solv == "SU2" ]]; then
      ext=""
      polar_case_dir="../$polar_case"
      # Check if grid file exist.
      [ -e ../$polar_case.su2 ] && ext="su2"
      # Exit is file extension is not found.
      if [[ $ext == "" ]]; then
        printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Polar case to be used as starting case is not found $polar_case" | fold -sw 80
        exit 1
      fi
      su2_link="${polar_case#*/}.su2"
      # Remove all symbolic links if they exist.
      find -type l -delete

      # Create the symbolic links for the grid and meshlog files from the grid directory.
      ln -sf ../$polar_dir/$su2_link $su2_link
      ln -sf ../$polar_dir/meshlog meshlog
    fi

  else
    start_from_polar_case=false
    # Remove all symbolic links if they exist.
    find -type l -delete
    grid=()
    grid_dir=()
    grid_link=()
    for i in "${!grid_param[@]}"; do
      if [[ $i -lt ${#grid_param[@]}-1 ]] && $multi_mesh_files; then
        grid+=(${grid_param[0]}${grid_param[$i+1]})
        ext=""
      fi
      if [[ $i -eq 0 ]] && ! $multi_mesh_files; then
              grid+=(${grid_param[$i]})
        ext=""
      fi
      if [[ $solv == "FLUENT" ]]; then
        grid_dir+=("../../01-GRIDS/Fluent_Meters_${grid[$i]}")
        # Check if grid file exist.
        [ -e ${grid_dir[$i]}/${grid[$i]}.msh ] && ext="msh"
        [ -e ${grid_dir[$i]}/${grid[$i]}.msh.h5 ] && ext="msh.h5"
        # Exit if file extension is not found.
        if [[ $i -lt ${#grid_param[@]}-1 ]] && $multi_mesh_files; then
          if [[ $ext == "" ]]; then
            printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Grid file not found in ${grid_dir[$i]}" | fold -sw 80
            exit 1
          fi
        fi
        if [[ $i -eq 0 ]] && ! $multi_mesh_files; then
          if [[ $ext == "" ]]; then
            printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Grid file not found in ${grid_dir[$i]}" | fold -sw 80
            exit 1
          fi
        fi

      elif [[ $solv == "SU2" ]]; then
        ext=""
        grid_dir="../../01-GRIDS/SU2_Meters_${grid[$i]}"
        # Check if grid file exist.
        [ -e ${grid_dir[$i]}/${grid[$i]}.su2 ] && ext="su2"
        # Exit is file extension is not found.
        if [[ $ext == "" ]]; then
          printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Grid file not found in ${grid_dir[$i]}" | fold -sw 80
          exit 1
        fi
      fi


# Create the symbolic links for the grid and meshlog files from the grid directory.
if [[ $i -lt ${#grid_param[@]}-1 ]] && $multi_mesh_files; then
        # Check if meshlog file exist.
  if [ ! -f ${grid_dir[$i]}/${grid[$i]}.ansa.meshlog ]; then
          printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr meshlog file ${grid[$i]}.ansa.meshlog not found in ${grid_dir[$i]}" | fold -sw 80
          exit 1
        fi
        start_pattern_1="Running volume mesh: Volume_Mesh_Scenario"
        start_pattern_2="Final check neg vol auto fix"

        #if sed -n "/$start_pattern_1/,\$p" "${grid_dir[$i]}/${grid[$i]}.ansa.meshlog" | grep -q "1 volumes failed to be meshed"; then
        # Commented due to new situation where you have more then one volume meshes
        if sed -n "/$start_pattern_1/,\$p" "${grid_dir[$i]}/${grid[$i]}.ansa.meshlog" | grep -q "volumes failed to be meshed"; then
          printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Volume mesh for POLAR-$polr is not good. Check if the volume mesh was successfully generated. Mesh: ${grid[$i]}" | fold -sw 80
          exit 1
        fi
        if sed -n "/$start_pattern_2/,\$p" "${grid_dir[$i]}/${grid[$i]}.ansa.meshlog" | grep -q "Unfixed negative volume remains. Not good."; then
          printf "\n\e${RED}%1s\n\e${NC}" "ABORTED! Final mesh for POLAR‑$polr is not good. Check for negative volume. Mesh: ${grid[$i]}" | fold -sw 80
          exit 1
        fi

        grid_link+=("grid_${grid_param[$i+1]}.$ext")
        ln -sf ${grid_dir[$i]}/${grid[$i]}.$ext ${grid_link[$i]}
        ln -sf ${grid_dir[$i]}/${grid[$i]}.ansa.meshlog meshlog_${grid_param[$i+1]}


        if [ -f ${grid_dir[$i]}/inlet_plane_fan_1.msh ]; then
          inlet_plane_fan_1=true
          ln -sf ${grid_dir[$i]}/inlet_plane_fan_1.msh .
        fi
        if [ -f ${grid_dir[$i]}/inlet_plane_fan_2.msh ]; then
          inlet_plane_fan_2=true
          ln -sf ${grid_dir[$i]}/inlet_plane_fan_2.msh .
        fi
        
        
        if [ -f ${grid_dir[$i]}/exit_plane_fan_out_1.msh ]; then
          exit_plane_fan_out_1=true
          ln -sf ${grid_dir[$i]}/exit_plane_fan_out_1.msh .
        fi
        if [ -f ${grid_dir[$i]}/exit_plane_fan_out_2.msh ]; then
          exit_plane_fan_out_2=true
          ln -sf ${grid_dir[$i]}/exit_plane_fan_out_2.msh .
        fi
        
        
        if [ -f ${grid_dir[$i]}/exit_plane_core_out_1.msh ]; then
          exit_plane_core_out_1=true
          ln -sf ${grid_dir[$i]}/exit_plane_core_out_1.msh .
        fi
        if [ -f ${grid_dir[$i]}/exit_plane_core_out_2.msh ]; then
          exit_plane_core_out_2=true
          ln -sf ${grid_dir[$i]}/exit_plane_core_out_2.msh .
        fi

 
      fi

      if [[ $i -eq 0 ]] && ! $multi_mesh_files; then
        grid_link+=("grid.$ext")
        ln -sf ${grid_dir[$i]}/${grid[$i]}.$ext ${grid_link[$i]}
        ln -sf ${grid_dir[$i]}/${grid[$i]}.ansa.meshlog meshlog
        
       
        if [ -f ${grid_dir[$i]}/inlet_plane_fan_1.msh ]; then
          inlet_plane_fan_1=true
          ln -sf ${grid_dir[$i]}/inlet_plane_fan_1.msh .
        fi
        if [ -f ${grid_dir[$i]}/inlet_plane_fan_2.msh ]; then
          inlet_plane_fan_2=true
          ln -sf ${grid_dir[$i]}/inlet_plane_fan_2.msh .
        fi
      
     
        if [ -f ${grid_dir[$i]}/exit_plane_fan_out_1.msh ]; then
          exit_plane_fan_out_1=true
          ln -sf ${grid_dir[$i]}/exit_plane_fan_out_1.msh .
        fi
        if [ -f ${grid_dir[$i]}/exit_plane_fan_out_2.msh ]; then
          exit_plane_fan_out_2=true
          ln -sf ${grid_dir[$i]}/exit_plane_fan_out_2.msh .
        fi
    
   
        if [ -f ${grid_dir[$i]}/exit_plane_core_out_1.msh ]; then
          exit_plane_core_out_1=true
          ln -sf ${grid_dir[$i]}/exit_plane_core_out_1.msh .
        fi
        if [ -f ${grid_dir[$i]}/exit_plane_core_out_2.msh ]; then
          exit_plane_core_out_2=true
          ln -sf ${grid_dir[$i]}/exit_plane_core_out_2.msh .
        fi

      fi
    done
  fi
else
  # Read grid parameters for mesh generation.
  # In this case the mesh will be generated based on the inputs below.
  scel=${grid_param[0]}
  vcel=${grid_param[1]}
  minl=${grid_param[2]}
  maxl=${grid_param[3]}
  ypls=${grid_param[4]}
  blgr=${grid_param[5]}
  blhf=${grid_param[6]}
  drud=""
  delv=""
  dflp=""
  for i in "${rudd_param[@]}"; do
    if is_not_number "$i"; then
      drud=""
    else
      if (( $(echo "$i < 0" | bc -l) )); then
        drud=$drud$(awk "BEGIN { printf \"-%.3d\", $i*(-10) }")
      else
        drud=$drud$(awk "BEGIN { printf \"+%.3d\", $i*10 }")
      fi
    fi
  done
  for i in "${elev_param[@]}"; do
    if is_not_number "$i"; then
      delv=""
    else
      if (( $(echo "$i < 0" | bc -l) )); then
        delv=$delv$(awk "BEGIN { printf \"-%.3d\", $i*(-10) }")
      else
        delv=$delv$(awk "BEGIN { printf \"+%.3d\", $i*10 }")
      fi
    fi
  done
  for i in "${aile_param[@]}"; do
    if is_not_number "$i"; then
      dail=""
    else
      if (( $(echo "$i < 0" | bc -l) )); then
        dail=$dail$(awk "BEGIN { printf \"-%.3d\", $i*(-10) }")
      else
        dail=$dail$(awk "BEGIN { printf \"+%.3d\", $i*10 }")
      fi
    fi
  done
  for i in "${flap_param[@]}"; do
    if is_not_number "$i"; then
      dflp=""
    else
      if (( $(echo "$i < 0" | bc -l) )); then
        dflp=$dflp$(awk "BEGIN { printf \"-%.3d\", $i*(-10) }")
      else
        dflp=$dflp$(awk "BEGIN { printf \"+%.3d\", $i*10 }")
      fi
    fi
  done
  if [[ -z "$drud" ]]; then ru=""; else ru="_RU"; fi
  if [[ -z "$delv" ]]; then el=""; else el="_EL"; fi
  if [[ -z "$dflp" ]]; then fl=""; else fl="_FL"; fi
  grid=$acrt"_"$cnfg$ru$drud$el$delv$fl$dflp
fi


# Check and copy SET file.
# -----------------------
# Exit if the specified SET file does not exist.
if [ ! -f ../../00-SUPPORT/SET-"$nset" ]; then
  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter SET: File 00-SUPPORT/SET-$nset does not exist." | fold -sw 80
  exit 1
fi
# Copy SET file to polar directory.
if $multi_mesh_files; then
  for i in "${!grid_param[@]}"; do
    if [[ $i -gt 0 ]]; then
      cp ../../00-SUPPORT/SET-$nset SET-${nset}_${grid_param[$i]}
    fi
  done
elif [[ $stgy = "COLD" ]] && [[ ${#alpha_cl[@]} > 1 ]]; then
  for i in "${!alpha_cl[@]}"; do
    cp ../../00-SUPPORT/SET-$nset SET-${nset}_${alpha_cl[$i]}
  done
elif [[ $stgy = "COLD" ]] && [[ ${#beta_cy[@]} > 1 ]]; then
  for i in "${!beta_cy[@]}"; do
    cp ../../00-SUPPORT/SET-$nset SET-${nset}_${beta_cy[$i]}
  done
else
  cp ../../00-SUPPORT/SET-$nset .
fi

# Check and copy HPC file.
# -----------------------
# Exit if the specified HPC host file does not exist.
#if [ ! -f ../../00-SUPPORT/HPC-"$nhpc" ]; then
#  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter HPC: File 00-SUPPORT/HPC-$nhpc does not exist." | fold -sw 80
#  exit 1
#fi
# Copy HPC host file to polar directory.
#cp ../../00-SUPPORT/HPC-$nhpc .

# Check and copy UDF source files.
# ------------------------------
# Exit if the specified file does not exist.
#if [ ! -f ../../00-SUPPORT/coef_driver.c ]; then
#  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr . UDF source file coef_driver.c does not exist in the folder /00-SUPPORT." | fold -sw 80
#  exit 1
#fi
#if [ ! -f ../../00-SUPPORT/udf.h ]; then
#  printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr . UDF library file udf.h does not exist in the folder /00-SUPPORT." | fold -sw 80
#  exit 1
#fi

## Copy UDF files to polar directory.
#cp ../../00-SUPPORT/coef_driver.c .

#cp ../../00-SUPPORT/udf.h .




# Start the calculation of the flow parameters.
# --------------------------------------------

hpft=()
T=()
p=()
rho=()
mu=()
ssp=()
Reynolds=()
ptot=()
qdin=()
qimp=()
Ttot=()
Cpsp=()
vel=()

for i in ${!mach_vel[@]}; do
  # In case altitude pressure HP is provided.
  if [[ $rehp_mode == "ALT" ]]; then
    hpft+=($(printf "%.10f" $(echo ${rehp_param[0]})))
  else
    # In case Reynolds number RE is provided.
    reyn=$(printf "%.10f" $(echo ${rehp_param[0]}))
    if (( $(echo "$reyn < 0" | bc -l) )); then
      printf "\n\e${RED}%1s\n%1s\n\n%1s\n\e${NC}" "Error: POLAR-$polr Parameter REY[ALT]" "Reynolds number cannot be negative." "REY[ALT]: $(param_descrip "REY[ALT]")" | fold -sw 80
      exit 1
    fi
    # Altitude in meters given Mach number, Reynolds number and reference chord.
    hpmt=$(pressure_altitude ${mach_vel[$i]} $reyn $cref $isad)
    # Meters to feet
    _hpft=$(awk "BEGIN {printf \"%.10f\", $hpmt/0.3048}")
    # If necessary, altitude is adjusted to match desired Reynolds for a given delta ISA.
    printf "\n\n%1s" "Matching Reynolds ..."
    count=0
    while true; do
      # Air free-stream static temperature.
      _T=$(temperature $_hpft $isad)
      # Air free-stream static pressure.
      _p=$(pressure $_hpft 0)
      # Air free-stream density.
      _rho=$(density $_hpft $isad)
      # Air free-stream dynamic viscosity.
      _mu=$(viscosity $_hpft $isad)
      # Air free-stream sound speed.
      _ssp=$(sound_speed $_hpft $isad)
      # Calculate Reynolds number.
      _Reynolds=$(awk "BEGIN {printf \"%.10f\", $_rho*${mach_vel[$i]}*$_ssp*$cref/$_mu}")
      printf "\n%.6E" $_Reynolds
      delta_rey=$(awk "BEGIN {printf \"%.10f\",  $_Reynolds - $reyn}")
      tol=1
      if (( $(echo "${delta_rey#-} < $tol" | bc -l) )); then
        break
      fi
      #echo $count
      #echo $hpft
      #echo $delta_rey
      _hpft=$(awk "BEGIN {printf \"%.10f\", $_hpft + 0.001*$delta_rey}")
      count=$(awk "BEGIN {printf \"%d\", $count + 1}")
    done
    hpft+=($_hpft)
  fi
  # Air free-stream static temperature.
  T+=($(temperature ${hpft[$i]} $isad))
  # Air free-stream static pressure.
  p+=($(pressure ${hpft[$i]} 0))
  # Air free-stream density.
  rho+=($(density ${hpft[$i]} $isad))
  # Air free-stream dynamic viscosity.
  mu+=($(viscosity ${hpft[$i]} $isad))
  # Air free-stream sound speed.
  ssp+=($(sound_speed ${hpft[$i]} $isad))
  # Reynolds number.
  Reynolds+=($(awk "BEGIN {printf \"%.10f\", ${rho[$i]}*${mach_vel[$i]}*${ssp[$i]}*$cref/${mu[$i]}}"))
  # Flow total pressure.
  ptot+=($(awk "BEGIN {printf \"%.10f\", ${p[$i]}*(1 + ($(cnt gam) - 1)/2*${mach_vel[$i]}**2)**($(cnt gam)/($(cnt gam) - 1))}"))
  # Flow dynamic pressure (incompressible definition 0.5*rho*V**2).
  qdin+=($(awk "BEGIN {printf \"%.10f\", $(cnt gam)/2*${p[$i]}*${mach_vel[$i]}**2}"))
  # Flow impart pressure (ptot - p).
  qimp+=($(awk "BEGIN {printf \"%.10f\", ${ptot[$i]} - ${p[$i]}}"))
  # Flow total temperature.
  Ttot+=($(awk "BEGIN {printf \"%.10f\", ${T[$i]}*(1 + ($(cnt gam) - 1)/2*${mach_vel[$i]}**2)}"))
  # Pressure coefficient at the stagnation point.
  Cpsp+=($(awk "BEGIN {printf \"%.10f\", 2/($(cnt gam)*${mach_vel[$i]}**2)*(${ptot[$i]}/${p[$i]} - 1)}"))
  # Air free-stream velocity.
  vel+=($(awk "BEGIN {printf \"%.10f\", ${mach_vel[$i]}*${ssp[$i]}}"))
done




# Create "infout" file with all the necessary information to be used in post processing.
# -------------------------------------------------------------------------------------
# Output the aicraft geometric reference data.
echo ""
echo ""
printf "\e${YELLOW}%4s %s\n\e${NC}" "                                    POLAR " "$polr"
printf "\e${YELLOW}%4s\n\e${NC}" "                                   ============"
echo -e "${LGRAY}"
printf "%81s\n"   "                                       JAMAL                                      "         > infout
printf "%81s\n"   "          Job Automation and Management of Aerodynamic simuLations (CFD)          "         >> infout
printf "%8s%s\n"  "                                 version: " "$version"                                      >> infout
printf "%8s\n"    "                                                                                  "         >> infout
printf "%81s\n"   "=================================[REFERENCE_DATA]================================="         | tee -a infout
echo ""
printf "%14s %s\n%14s %s\n%14s %s\n%14s %s\n%14s %s\n\n" "POLAR:" "$polr" "AIRCRAFT:" "$acrt"  "CONFIGURATION:" "$cnfg" "DIMENSION_REF:" "REF-$nref" "NUMERIC_SET:" "SET-$nset"        | tee -a infout
printf "%14s%12.3f %15s%12.3f %15s%12.3f\n" \
"SREF[m2]:" "$sref" "CREF[m]:" "$cref" "BREF[m]:" "$bref"                                                      | tee -a infout
printf "\n%14s%12.3f %15s%12.3f %15s%12.3f\n" \
"XREF[m]:" "$xref" "YREF[m]:" "$yref" "ZREF[m]:" "$zref"                                                       | tee -a infout

# Output the flow condition for each Mach number/velocity.
for i in ${!mach_vel[@]}; do
  printf "\n%81s\n" "=================================[FLOW_CONDITION]================================="       | tee -a infout
  if is_not_number "${Reynolds[$i]}"; then fmt_r=%7s; else fmt_r=%7.1E; fi
  if is_not_number "${hpft[$i]}"; then fmt_h=%7s; else fmt_h=%7.0f; fi
  printf "\n%14s%12.0f %15s%12.3f %15s%12.3f\n" \
  "HP[ft]:" "${hpft[$i]}" "p[Pa]:" "${p[$i]}" "T[K]:" "${T[$i]}"                                               | tee -a infout
  printf "\n%14s%12.3f %15s%12.3f %15s%12.3f\n" \
  "Mach:" "${mach_vel[$i]}" "ptot[Pa]:" "${ptot[$i]}" "Ttot[K]:" "${Ttot[$i]}"                                 | tee -a infout
  printf "\n%14s%12.3f %15s%12.3f %15s%12.3f\n" \
  "ISAD[K]:" "$isad" "qdin[Pa]:" "${qdin[$i]}" "rho[kg/m3]:" "${rho[$i]}"                                      | tee -a infout
  printf "\n%14s%12.3E %15s%12.3f %15s%12.3f\n" \
  "Reynolds:" "${Reynolds[$i]}" "qimp[Pa]:" "${qimp[$i]}" "a[m/s]:" "${ssp[$i]}"                               | tee -a infout
  printf "\n%14s%12.3f %15s%12.3E %15s%12.3f\n" \
  "V[m/s]:" "${vel[$i]}" "mu[Pa.s]:" "${mu[$i]}" "Cpstag:" "${Cpsp[$i]}"                                       | tee -a infout
done

# Output the the rudder geometric data and deflection to the "infout" file.
printf "\n%81s\n" "====================================[RUDDER]======================================"         | tee -a infout
echo -e "${LGRAY}"
for rudd in "${rudd_REF[@]}"; do
  i=$(awk "BEGIN {print $rudd - 1}")
  if is_not_number "${rudd_param[$i]}"; then fmt=%7s; else fmt=%7.3f; fi
  printf "%-5s$fmt\n%-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f\n" \
  "RUD$rudd:" "${rudd_param[$i]}"\
  "X0R$rudd:" "${x0hr_REF[$i]}" "Y0R$rudd:" "${y0hr_REF[$i]}" "Z0R$rudd:" "${z0hr_REF[$i]}"\
  "DXR$rudd:" "${dxhr_REF[$i]}" "DYR$rudd:" "${dyhr_REF[$i]}" "DZR$rudd:" "${dzhr_REF[$i]}"                    | tee -a infout
done

# Output the the elevon geometric data and deflection to the "infout" file.
printf "\n%81s\n" "====================================[ELEVON]======================================"         | tee -a infout
echo -e "${LGRAY}"
for elev in "${elev_REF[@]}"; do
  i=$(awk "BEGIN {print $elev - 1}")
  if is_not_number "${elev_param[$i]}"; then fmt=%7s; else fmt=%7.3f; fi
  printf "%-5s$fmt\n%-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f\n" \
  "ELV$elev:" "${elev_param[$i]}"\
  "X0E$elev:" "${x0he_REF[$i]}" "Y0E$elev:" "${y0he_REF[$i]}" "Z0E$elev:" "${z0he_REF[$i]}"\
  "DXE$elev:" "${dxhe_REF[$i]}" "DYE$elev:" "${dyhe_REF[$i]}" "DZE$elev:" "${dzhe_REF[$i]}"                    | tee -a infout
done

# Output the the aileron geometric data and deflection to the "infout" file.
printf "\n%81s\n" "===================================[AILERON]======================================"         | tee -a infout
echo -e "${LGRAY}"
for aile in "${aile_REF[@]}"; do
  i=$(awk "BEGIN {print $aile - 1}")
  if is_not_number "${aile_param[$i]}"; then fmt=%7s; else fmt=%7.3f; fi
  printf "%-5s$fmt\n%-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f\n" \
  "AIL$aile:" "${aile_param[$i]}"\
  "X0A$aile:" "${x0ha_REF[$i]}" "Y0A$aile:" "${y0ha_REF[$i]}" "Z0A$aile:" "${z0ha_REF[$i]}"\
  "DXA$aile:" "${dxha_REF[$i]}" "DYA$aile:" "${dyha_REF[$i]}" "DZA$aile:" "${dzha_REF[$i]}"                    | tee -a infout
done

# Output the the flap geometric data and deflection to the "infout" file.
printf "\n%81s\n" "=====================================[FLAP]======================================="         | tee -a infout
echo -e "${LGRAY}"
for flap in "${flap_REF[@]}"; do
  i=$(awk "BEGIN {print $flap - 1}")
  if is_not_number "${flap_param[$i]}"; then fmt=%7s; else fmt=%7.3f; fi
  printf "%-5s$fmt\n%-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f\n" \
  "FLP$flap:" "${flap_param[$i]}"\
  "X0F$flap:" "${x0hf_REF[$i]}" "Y0F$flap:" "${y0hf_REF[$i]}" "Z0F$flap:" "${z0hf_REF[$i]}"\
  "DXF$flap:" "${dxhf_REF[$i]}" "DYF$flap:" "${dyhf_REF[$i]}" "DZF$flap:" "${dzhf_REF[$i]}"                    | tee -a infout
done

# Output the the propeller geometric data to the "infout" file.
printf "\n%81s\n" "===================================[PROPELLER]===================================="         | tee -a infout
echo -e "${LGRAY}"
for prop in "${prop_REF[@]}"; do
  i=$(awk "BEGIN {print $prop - 1}")
  printf "%-5s%7.0f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f  %-5s%7.3f\n%-5s%7.3f  %-5s%7.3f  %-5s%7.3f\n" \
  "NBL$prop:" "${nbld_REF[$i]}" "DIA$prop:" "${diam_REF[$i]}" "CRD$prop:" "${chor_REF[$i]}"\
  "XHU$prop:" "${xhub_REF[$i]}" "YHU$prop:" "${yhub_REF[$i]}" "ZHU$prop:" "${zhub_REF[$i]}"\
  "XTI$prop:" "${xtil_REF[$i]}" "YTI$prop:" "${ytil_REF[$i]}" "ZTI$prop:" "${ztil_REF[$i]}"     | tee -a infout
done

# Read the PIDs from the meshlog file and output to the "infout" file.
printf "\n%81s\n" "=====================================[ZONES]======================================"         | tee -a infout
echo -e "${LGRAY}"
# Read meshlog file and find the line containing the Fluid PID and convert to lowercase.
if $multi_mesh_files; then
  meshlog_file=meshlog_${grid_param[1]}
else
  meshlog_file=meshlog
fi
matched_line=$(grep -m 1 "Fluid: " "$meshlog_file")
fluid=$(echo "$matched_line" | awk -F "Fluid: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
# Read meshlog file and find the line containing the Dimension info and convert to lowercase.
matched_line=$(grep -m 1 "Dimension: " "$meshlog_file")
dim=$(echo "$matched_line" | awk -F "Dimension: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
# Read meshlog file and find the line containing the wall PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Wall PIDs: " "$meshlog_file")
pid_wall=$(echo "$matched_line" | awk -F "Wall PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_wall" ]]; then pid_wall="-"; fi
# Read meshlog file and find the line containing the farfield PID and convert to lowercase.
matched_line=$(grep -m 1 "Farfield PIDs: " "$meshlog_file")
pid_far=$(echo "$matched_line" | awk -F "Farfield PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_far" ]]; then pid_far="-"; fi

matched_line=$(grep -m 1 "Farfield IDs: " "$meshlog_file")
id_far=$(echo "$matched_line" | awk -F "Farfield IDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$id_far" ]]; then id_far=("-"); fi

# Read meshlog file and find the line containing the symmetry PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Symmetry PIDs: " "$meshlog_file")
pid_sym=$(echo "$matched_line" | awk -F "Symmetry PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_sym" ]]; then pid_sym="-"; fi
# Read meshlog file and find the line containing the propeller PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Prop_Disk PIDs: " "$meshlog_file")
pid_disk=$(echo "$matched_line" | awk -F "Prop_Disk PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_disk" ]]; then pid_disk="-"; fi

# Read meshlog file and find the line containing the fan inlet PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Fan_Inlet PIDs: " "$meshlog_file")
pid_fan_inlet=$(echo "$matched_line" | awk -F "Fan_Inlet PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_fan_inlet" ]]; then pid_fan_inlet="-"; fi

matched_line=$(grep -m 1 "Fan_Inlet IDs: " "$meshlog_file")
id_fan_inlet=($(echo "$matched_line" | awk -F "Fan_Inlet IDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}'))
if [[ -z "$id_fan_inlet" ]]; then id_fan_inlet=("-"); fi

# Read meshlog file and find the line containing the fan outlet PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Fan_Outlet PIDs: " "$meshlog_file")
pid_fan_outlet=$(echo "$matched_line" | awk -F "Fan_Outlet PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_fan_outlet" ]]; then pid_fan_outlet="-"; fi

# Read meshlog file and find the line containing the core outlet PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Core_Outlet PIDs: " "$meshlog_file")
pid_core_outlet=$(echo "$matched_line" | awk -F "Core_Outlet PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_core_outlet" ]]; then pid_core_outlet="-"; fi

# Read meshlog file and find the line containing the fan inlet PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Flow_Thru_Plane PIDs: " "$meshlog_file")
pid_flow_thru_plane=$(echo "$matched_line" | awk -F "Flow_Thru_Plane PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_flow_thru_plane" ]]; then pid_flow_thru_plane="-"; fi


if [[ -z "$pid_disk" ]]; then pid_disk="-"; fi
# Read meshlog file and find the line containing the ground PIDs and convert to lowercase.
matched_line=$(grep -m 1 "Ground PIDs: " "$meshlog_file")
pid_grd=$(echo "$matched_line" | awk -F "Ground PIDs: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')
if [[ -z "$pid_grd" ]]; then pid_grd="-"; fi
#done

pid_rud1="-"
pid_rud2="-"
pid_elv1="-"
pid_elv2="-"
pid_elv3="-"
pid_elv4="-"
# pid_fan_inlet="-"
# pid_fan_outlet="-"
# pid_core_exhaust="-"

pid_wing=()
pid_body=()
pid_vtail=()
pid_vtail_rh=()
pid_htail=()
pid_flap=()
pid_aileron=()
pid_aileron_rh=()
pid_nowing=()
pid_nobody=()
pid_novtail=()
pid_novtail_rh=()
pid_nohtail=()
pid_noflap=()
pid_noaileron=()
pid_noaileron_rh=()


pid_wall_list=($pid_wall)
for pid in ${pid_wall_list[@]}; do
  if [[ $pid == w* && $pid != *-rh ]]; then pid_wing+="$pid "; fi
  if [[ $pid == b* && $pid != *-rh ]]; then pid_body+="$pid "; fi
  if [[ $pid == v* && $pid != *-rh ]]; then pid_vtail+="$pid "; fi
  if [[ $pid == v* && $pid == *-rh ]]; then pid_vtail_rh+="$pid "; fi
  if [[ $pid == h* && $pid != *-rh ]]; then pid_htail+="$pid "; fi
  if [[ $pid == w.flp* && $pid != *-rh ]]; then pid_flap+="$pid "; fi
  if [[ $pid == w.ail* && $pid != *-rh ]]; then pid_aileron+="$pid "; fi
  if [[ $pid == w.ail* && $pid == *-rh ]]; then pid_aileron_rh+="$pid "; fi
done

for pid in ${pid_wall_list[@]}; do
  if [[ $pid != w* ]] && [[ $pid_wing != "" ]]; then pid_nowing+="$pid "; fi
  if [[ $pid != b* ]] && [[ $pid_body != "" ]]; then pid_nobody+="$pid "; fi
  if [[ $pid != v* ]] && [[ $pid_vtail != "" ]]; then pid_novtail+="$pid "; fi
  if [[ $pid != v* ]] && [[ $pid_vtail_rh != "" ]]; then pid_novtail_rh+="$pid "; fi
  if [[ $pid != h* ]] && [[ $pid_htail != "" ]]; then pid_nohtail+="$pid "; fi
  if [[ $pid != w.flp* ]] && [[ $pid_flap != "" ]]; then pid_noflap+="$pid "; fi
  if [[ $pid != w.ail* ]] && [[ $pid_aileron != "" ]]; then pid_noaileron+="$pid "; fi
  if [[ $pid != w.ail* ]] && [[ $pid_aileron_rh != "" ]]; then pid_noaileron_rh+="$pid "; fi
done

if [[ $pid_wing == ""  ]]; then pid_wing="-"; fi
if [[ $pid_nowing == ""  ]]; then pid_nowing="-"; fi
if [[ $pid_body == ""  ]]; then pid_body="-"; fi
if [[ $pid_nobody == ""  ]]; then pid_nobody="-"; fi
if [[ $pid_vtail == ""  ]]; then pid_vtail="-"; fi
if [[ $pid_vtail_rh == ""  ]]; then pid_vtail_rh="-"; fi
if [[ $pid_novtail == ""  ]]; then pid_novtail="-"; fi
if [[ $pid_novtail_rh == ""  ]]; then pid_novtail_rh="-"; fi
if [[ $pid_htail == ""  ]]; then pid_htail="-"; fi
if [[ $pid_nohtail == ""  ]]; then pid_nohtail="-"; fi
if [[ $pid_flap == ""  ]]; then pid_flap="-"; fi
if [[ $pid_noflap == ""  ]]; then pid_noflap="-"; fi
if [[ $pid_aileron == ""  ]]; then pid_aileron="-"; fi
if [[ $pid_aileron_rh == ""  ]]; then pid_aileron_rh="-"; fi
if [[ $pid_noaileron == ""  ]]; then pid_noaileron="-"; fi
if [[ $pid_noaileron_rh == ""  ]]; then pid_noaileron_rh="-"; fi



declare -A pid_prop=()
for pid in $pid_disk; do
  # Extract the number after the last hyphen
  number=${pid##*-}

  # Remove leading zeros
  if [[ -z $number ]]; then
    num=0
  else
    num=$((10#$number))
  fi

  # Append the word to the corresponding group in the associative array
  pid_prop["$num"]+="$pid "
done

printf "%-13s %-13s\n\n" "WALL:" "$pid_wall"                  | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "FARFIELD:" "$pid_far"               | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "SYMMETRY:" "$pid_sym"               | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "GROUND:" "$pid_grd"                 | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "WING:" "$pid_wing"                  | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOWING:" "$pid_nowing"              | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "BODY:" "$pid_body"                  | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOBODY:" "$pid_nobody"              | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "VTAIL:" "$pid_vtail"                | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOVTAIL:" "$pid_novtail"            | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "VTAIL_RH:" "$pid_vtail_rh"          | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOVTAIL_RH:" "$pid_novtail_rh"      | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "HTAIL:" "$pid_htail"                | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOHTAIL:" "$pid_nohtail"            | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "FLAP:" "$pid_flap"                  | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOFLAP:" "$pid_noflap"              | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "AILERON:" "$pid_aileron"            | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOAILERON:" "$pid_noaileron"        | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "AILERON_RH:" "$pid_aileron_rh"      | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "NOAILERON_RH:" "$pid_noaileron_rh"  | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "FANINLET:" "$pid_fan_inlet"         | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "FANOULET:" "$pid_fan_outlet"        | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "COREEXHA:" "$pid_core_outlet"       | fold -sw 80 | tee -a infout
printf "%-13s %-13s\n\n" "FLOW_THRU_PL:" "$pid_flow_thru_plane"   | fold -sw 80 | tee -a infout
for i in "${prop_REF[@]}"; do
  if [[ ${pid_prop[$i]} != "" ]]; then
printf "%-13s %-13s\n\n" "PROPELLER$i:" "${pid_prop[$i]}"     | fold -sw 80 | tee -a infout
  else
    printf "%-13s %-13s\n\n" "PROPELLER$i:" "-"               | fold -sw 80 | tee -a infout
  fi
done

# Commented if not in use
# Actuator disk
DPpro=()
xprop=()
yprop=()
zprop=()
omega=()
count=0
for i in "${!prop_REF[@]}"; do
#for i in "${!prop_param[@]}"; do
  if [[ ${prop_param[$i+$count]} != "-" ]]; then       
    Tprop=$(awk "BEGIN {printf \"%.3f\", ${prop_param[$i+$count]}*0.5*${rho[0]}*${vel[0]} ^ 2*$sref}")
    Adisk=$(awk "BEGIN {printf \"%.3f\", 3.141592653589793*(${diam_REF[$i]}/2) ^ 2}")
    DPpro+=($(awk "BEGIN {printf \"%.3f\", $Tprop/$Adisk}"))
    xprop+=(${xhub_REF[$i]})
    yprop+=(${yhub_REF[$i]})
    zprop+=(${zhub_REF[$i]})
    omega+=(${prop_param[$i+1+$count]})
  else
    DPpro+=("-")
    xprop+=("-")
    yprop+=("-")
    zprop+=("-")
    omega+=("-")
  fi
  count=$(awk "BEGIN {printf \"%d\", $count + 1}")
done

fan_inlet_mass_flow=()
fan_inlet_total_temp=()
fan_inlet_stat_pressure=()
fan_inlet_pmax=()
fan_inlet_pmin=()
fan_outlet_total_pressure=()
fan_outlet_total_temp=()
fan_outlet_stat_pressure=()
core_outlet_total_pressure=()
core_outlet_total_temp=()
core_outlet_stat_pressure=()
for i in "${!fani_param[@]}"; do
  if [[ ${fani_param[$i]} != "-" ]]; then
    fan_inlet_mass_flow+=(${fani_param[$i]})
    fan_inlet_total_temp+=($(awk "BEGIN {printf \"%.3f\", ${Ttot[0]}}"))
    fan_inlet_stat_pressure+=($(awk "BEGIN {printf \"%.3f\", ${p[0]}}"))
    fan_inlet_pmax+=($(awk "BEGIN {printf \"%.3f\", ${fan_inlet_stat_pressure[$i]} * 1.4 }"))
    fan_inlet_pmin+=($(awk "BEGIN {printf \"%.3f\", ${fan_inlet_stat_pressure[$i]} * 0.4 }"))
  else
    fan_inlet_mass_flow+=("-")
    fan_inlet_total_temp+=("-")
    fan_inlet_stat_pressure+=("-")
    fan_inlet_pmax+=("-")
    fan_inlet_pmin+=("-")
  fi
done

count_fano=0
for i in "${!fano_param[@]}"; do
  if [[ $count_fano < 4 ]]; then
    if [[ ${fano_param[$i]} != "-" ]]; then
      fan_outlet_total_pressure+=(${fano_param[$i+$count_fano]})
      fan_outlet_total_temp+=(${fano_param[$i+$count_fano+1]})
      fan_outlet_stat_pressure+=($(awk "BEGIN {printf \"%.3f\", ${p[0]}}"))
      count_fano=$(awk "BEGIN {printf \"%d\", $count_fano + 1}")
    else
      fan_outlet_total_pressure+=("-")
      fan_outlet_total_temp+=("-")
      fan_outlet_stat_pressure+=("-")
    fi
  fi
done
count_fano=$(awk "BEGIN {printf \"%d\", ${count_fano}/2}")

count_core=0
for i in "${!core_param[@]}"; do
  if [[ $count_core < 4 ]]; then
    if [[ ${core_param[$i]} != "-" ]]; then
      core_outlet_total_pressure+=(${core_param[$i*$count_core]})
      core_outlet_total_temp+=(${core_param[$i+$count_core+1]})
      core_outlet_stat_pressure+=($(awk "BEGIN {printf \"%.3f\", ${p[0]}}"))
      count_core=$(awk "BEGIN {printf \"%d\", $count_core + 1}")
    else
      core_outlet_total_pressure+=("-")
      core_outlet_total_temp+=("-")
      core_outlet_stat_pressure+=("-")
    fi
  fi
done   
count_core=$(awk "BEGIN {printf \"%d\", ${count_core}/2}")    

#for i in "${fano_param[@]}"; do
#  echo $i
#done
#echo $count_fano
#exit

if [[ -f ../../00-SUPPORT/mfr.c ]]; then

  use_mfr="true"

  if [[ ${fan_inlet_mass_flow[0]} == "-" ]]; then
    use_mfr="false"
  fi

  cp ../../00-SUPPORT/mfr.c .
  cp ../../00-SUPPORT/udf.h .

  if [[ "$use_mfr" == "true" ]]; then
    substitute_input_variables_mfr_driver id_fan_inlet fan_inlet_mass_flow id_far
  fi
fi



# Substitute the input variables in the solver template file SET with the flow parameters and geometric data.
# ----------------------------------------------------------------------------------------------------------

#for (( kdx=0; kdx<${#mach_vel[@]}; kdx++  )); do
if [[ $stgy = "COLD" ]] && [[ ${#alpha_cl[@]} > 1 ]]; then
  for i in "${!alpha_cl[@]}"; do
    kdx=0
    substitute_input_variables_fluent ${vel[$kdx]} ${rho[$kdx]} ${p[$kdx]} ${T[$kdx]} ${mu[$kdx]} ${mach_vel[$kdx]} ${alpha_cl[$i]} ${grid_link[0]}
  done
elif [[ $stgy = "COLD" ]] && [[ ${#beta_cy[@]} > 1 ]]; then
  for i in "${!beta_cy[@]}"; do
    kdx=0
    substitute_input_variables_fluent ${vel[$kdx]} ${rho[$kdx]} ${p[$kdx]} ${T[$kdx]} ${mu[$kdx]} ${mach_vel[$kdx]} ${beta_cy[$i]} ${grid_link[0]}
  done
else
  for i in "${!grid_link[@]}"; do
    kdx=0
    substitute_input_variables_fluent ${vel[$kdx]} ${rho[$kdx]} ${p[$kdx]} ${T[$kdx]} ${mu[$kdx]} ${mach_vel[$kdx]} ${grid_param[$i+1]} ${grid_link[$i]}
  done
fi
#done


if [[ $alcl_mode == "CLS" ]] || [[ $becy_mode == "CYS"   ]]; then

  # Exit if the specified file does not exist.
  if [ ! -f ../../00-SUPPORT/coef_driver.c ]; then
    printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr . UDF source file coef_driver.c does not exist in the folder /00-SUPPORT." | fold -sw 80
    exit 1
  fi
  if [ ! -f ../../00-SUPPORT/udf.h ]; then
    printf "\n\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr . UDF library file udf.h does not exist in the folder /00-SUPPORT." | fold -sw 80
    exit 1
  fi
  # Copy UDF files to polar directory.
  cp ../../00-SUPPORT/coef_driver.c .
  cp ../../00-SUPPORT/udf.h .

  size_alcl=${#alpha_cl[@]}
  size_becy=${#beta_cy[@]}
  size_mach=${#mach_vel[@]}
  delta_iter=$(awk "BEGIN {printf \"%d\", 1000*${iter_param[2]}}")
  substitute_input_variables_coef_driver $size_mach "${mach_vel[@]}" $size_alcl "${alpha_cl[@]}" $size_becy "${beta_cy[@]}" $delta_iter $iter_update $iter_slope $iter_start $iter_next $cl_tol $cy_tol $da_slp $db_slp $da_max
fi

# Start case sequence creation.
# ----------------------------

# Get index of the closest positive alpha to zero.
idx_alcl_0=$(index_closest_to_value_zero "${alpha_cl[@]}")
idx_becy_0=$(index_closest_to_value_zero "${beta_cy[@]}")

# Output the case sequence to the "infout" file.
printf "%81s\n" "=====================================[CASES]======================================"                    | tee -a infout
echo -e "${LGRAY}"
printf "%-4s  %9s  %9s  %9s  %9s  %-21s  %9s\n" "CASE"  "MACH"  "REYNOLDS"  $alcl_mode  $becy_mode  "NAME"  "ITERS"     | tee -a infout


for (( kdx=0; kdx<${#mach_vel[@]}; kdx++ )); do
  # Check if the closest positive alpha to zero is greater than the first alpha in the sequence.
  if (( $(echo "${alpha_cl[$idx_alcl_0]} > ${alpha_cl[0]}" | bc -l) )) && (( $(echo "${alpha_cl[-1]} > ${alpha_cl[$idx_alcl_0]}" | bc -l) )); then

    # Beta loop starting from the closest positive beta to zero up to the maximum beta.
    for (( jdx=0; jdx<${#beta_cy[@]}; jdx++ )); do
      if [[ $jdx -ge $idx_becy_0  ]]; then
        malt90=1

        # Alpha loop starting from the closest positive alpha to zero up to the maximum alpha.
        for (( idx=0; idx<${#alpha_cl[@]}; idx++ )); do
          if [[ $idx -ge $idx_alcl_0 ]]; then
            if [[ $idx -eq $idx_alcl_0 ]] && $start_from_polar_case ; then
              echo ";Read polar case from $polar_case." > SET-$nset

                trn_file="FLUENT_LOG"
                if [ -e $trn_file ]; then
                  trn_command="/file/start-transcript $trn_file ok"
                else
                  trn_command="/file/start-transcript $trn_file"
                fi
                echo "$trn_command" >> SET-$nset

              echo "rc $cas_link" >> SET-$nset
              echo "rd $dat_link" >> SET-$nset
              echo ";" >> SET-$nset
              printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
              malt90=$(awk "BEGIN {print $malt90 + 1}")
            else
              set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
            fi
          fi
        done
        if (( $(echo "$kdx == ${#mach_vel[@]}-1" | bc -l) )); then
          if ! $multi_mesh_files && [[ $stgy = "WARM" ]]; then
            read_case_data_jou >> SET-$nset
          fi
        fi
        # Alpha loop starting from the closest negative alpha to zero up to the minimum alpha.
        for (( idx=${#alpha_cl[@]}-1; idx>=0 ; idx-- )); do
          if [[ $idx -lt $idx_alcl_0 ]]; then
            if [[ $idx -eq $idx_alcl_0 ]] && $start_from_polar_case ; then
              echo ";Read polar case from $polar_case." > SET-$nset

                trn_file="FLUENT_LOG"
                if [ -e $trn_file ]; then
                  trn_command="/file/start-transcript $trn_file ok"
                else
                  trn_command="/file/start-transcript $trn_file"
                fi
                echo "$trn_command" >> SET-$nset

              echo "rc $cas_link" >> SET-$nset
              echo "rd $dat_link" >> SET-$nset
              echo ";" >> SET-$nset
              printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
              malt90=$(awk "BEGIN {print $malt90 + 1}")
            else
              set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
            fi
          fi
        done
        if (( $(echo "$kdx == ${#mach_vel[@]}-1" | bc -l) )); then
          if ! $multi_mesh_files && [[ $stgy = "WARM" ]]; then
            exit_jou >> SET-$nset
          fi
        fi
      fi
    done
  else
    # Check if the closest positive beta to zero is greater than the first beta in the sequence.
    if (( $(echo "${beta_cy[$idx_becy_0]} > ${beta_cy[0]}" | bc -l) )) && (( $(echo "${beta_cy[-1]} > ${beta_cy[$idx_becy_0]}" | bc -l)  )); then
      # Alpha loop starting from the closest positive alpha to zero up to the maximum alpha.
      for (( idx=0; idx<${#alpha_cl[@]}; idx++ )); do
        if [[ $idx -ge $idx_alcl_0 ]]; then
          malt90=1

          # Beta loop starting from the closest positive beta to zero up to the maximum beta.
          for (( jdx=0; jdx<${#beta_cy[@]}; jdx++ )); do
            if [[ $jdx -ge $idx_becy_0 ]]; then
              if [[ $jdx -eq $idx_becy_0 ]] && $start_from_polar_case ; then
                echo ";Read polar case from $polar_case." > SET-$nset

                  trn_file="FLUENT_LOG"
                  if [ -e $trn_file ]; then
                    trn_command="/file/start-transcript $trn_file ok"
                  else
                    trn_command="/file/start-transcript $trn_file"
                  fi
                  echo "$trn_command" >> SET-$nset

                echo "rc $cas_link" >> SET-$nset
                echo "rd $dat_link" >> SET-$nset
                echo ";" >> SET-$nset
                printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
                malt90=$(awk "BEGIN {print $malt90 + 1}")
              else
                set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
              fi
            fi
          done
          if (( $(echo "$kdx == ${#mach_vel[@]}-1" | bc -l) )); then
            if ! $multi_mesh_files && [[ $stgy = "WARM" ]]; then
              read_case_data_jou >> SET-$nset
            fi
          fi

          # Beta loop starting from the closest negative beta to zero up to the minimum beta.
          for (( jdx=${#beta_cy[@]}-1; jdx>=0 ; jdx-- )); do
            if [[ $jdx -lt $idx_becy_0 ]]; then
              if [[ $jdx -eq $idx_becy_0 ]] && $start_from_polar_case ; then
                echo ";Read polar case from $polar_case." > SET-$nset

                  trn_file="FLUENT_LOG"
                  if [ -e $trn_file ]; then
                    trn_command="/file/start-transcript $trn_file ok"
                  else
                    trn_command="/file/start-transcript $trn_file"
                  fi
                  echo "$trn_command" >> SET-$nset

                echo "rc $cas_link" >> SET-$nset
                echo "rd $dat_link" >> SET-$nset
                echo ";" >> SET-$nset
                printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
                malt90=$(awk "BEGIN {print $malt90 + 1}")
              else
                set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
              fi
            fi
          done
          if (( $(echo "$kdx == ${#mach_vel[@]}-1" | bc -l) )); then
            if ! $multi_mesh_files && [[ $stgy = "WARM" ]]; then
              exit_jou >> SET-$nset
            fi
          fi
        fi
      done
    else
      # Check if the minimum beta is equal to the maximum beta.
      if (( $(echo "${beta_cy[0]} == ${beta_cy[-1]}" | bc -l) )); then
        # Beta loop starting from the closest beta to zero upto the maximum positive beta.
        for (( jdx=0; jdx<${#beta_cy[@]}; jdx++ )); do
          malt90=1

          if (( $(echo "${alpha_cl[0]} >= 0" | bc -l)  )); then
            # Alpha loop starting from the closest alpha to zero upto the maximum positive alpha.
            for (( idx=0; idx<${#alpha_cl[@]}; idx++ )); do
              if [[ $idx -eq $idx_alcl_0 ]] && $start_from_polar_case ; then
                echo ";Read polar case from $polar_case." > SET-$nset

                  trn_file="FLUENT_LOG"
                  if [ -e $trn_file ]; then
                    trn_command="/file/start-transcript $trn_file ok"
                  else
                    trn_command="/file/start-transcript $trn_file"
                  fi
                  echo "$trn_command" >> SET-$nset

                echo "rc $cas_link" >> SET-$nset
                echo "rd $dat_link" >> SET-$nset
                echo ";" >> SET-$nset
                printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
                malt90=$(awk "BEGIN {print $malt90 + 1}")
              else
                set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
              fi
            done
          else
            # Alpha loop starting from the closest alpha to zero upto the maximum negative alpha.
            for (( idx=${#alpha_cl[@]}-1; idx>=0 ; idx-- )); do
              if [[ $idx -le $idx_alcl_0 ]]; then
                if [[ $idx -eq $idx_alcl_0 ]] && $start_from_polar_case ; then
                  echo ";Read polar case from $polar_case." > SET-$nset

                    trn_file="FLUENT_LOG"
                    if [ -e $trn_file ]; then
                      trn_command="/file/start-transcript $trn_file ok"
                    else
                      trn_command="/file/start-transcript $trn_file"
                    fi
                    echo "$trn_command" >> SET-$nset

                  echo "rc $cas_link" >> SET-$nset
                  echo "rd $dat_link" >> SET-$nset
                  echo ";" >> SET-$nset
                  printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
                  malt90=$(awk "BEGIN {print $malt90 + 1}")
                else
                  set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
                fi
              fi
            done
          fi
          if (( $(echo "$kdx == ${#mach_vel[@]}-1" | bc -l) )); then
            if ! $multi_mesh_files && [[ $stgy = "WARM" ]]; then
              exit_jou >> SET-$nset
            fi
          fi
        done
      else
        # Alpha loop starting from the closest alpha to zero upto the maximum positive alpha.
        for (( idx=0; idx<${#alpha_cl[@]}; idx++ )); do
          malt90=1

          if (( $(echo "${beta_cy[0]} >= 0" | bc -l)  )); then
            # Beta loop starting from the closest beta to zero upto the maximum positive beta.
            for (( jdx=0; jdx<${#beta_cy[@]}; jdx++ )); do
              if [[ $jdx -eq $idx_becy_0 ]] && $start_from_polar_case ; then
                echo ";Read polar case from $polar_case." > SET-$nset

                  trn_file="FLUENT_LOG"
                  if [ -e $trn_file ]; then
                    trn_command="/file/start-transcript $trn_file ok"
                  else
                    trn_command="/file/start-transcript $trn_file"
                  fi
                  echo "$trn_command" >> SET-$nset

                echo "rc $cas_link" >> SET-$nset
                echo "rd $dat_link" >> SET-$nset
                echo ";" >> SET-$nset
                printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
                malt90=$(awk "BEGIN {print $malt90 + 1}")
              else
                set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
              fi
            done
          else
            # Beta loop starting from the closest beta to zero upto the maximum negative beta.
            for (( jdx=${#beta_cy[@]}-1; jdx>=0 ; jdx-- )); do
              if [[ $jdx -le $idx_becy_0 ]]; then
                if [[ $jdx -eq $idx_becy_0 ]] && $start_from_polar_case ; then
                  echo ";Read polar case from $polar_case." > SET-$nset

                    trn_file="FLUENT_LOG"
                    if [ -e $trn_file ]; then
                      trn_command="/file/start-transcript $trn_file ok"
                    else
                      trn_command="/file/start-transcript $trn_file"
                    fi
                    echo "$trn_command" >> SET-$nset

                  echo "rc $cas_link" >> SET-$nset
                  echo "rd $dat_link" >> SET-$nset
                  echo ";" >> SET-$nset
                  printf "%04d  %9.3f  %9.3E  %9.2f  %9.2f  %-21s  %9d\n" "$malt90" ${mach_vel[$kdx]} ${Reynolds[$kdx]} ${alpha_cl[$idx]} ${beta_cy[$jdx]} "$polar_case_filename" "0000" | tee -a infout
                  malt90=$(awk "BEGIN {print $malt90 + 1}")
                else
                  set_flow_cond_sequence ${alpha_cl[$idx]} ${beta_cy[$jdx]} ${mach_vel[$kdx]} ${Reynolds[$kdx]} $iter_param $malt90 $dim $pid_far ${p[$kdx]} ${T[$kdx]} $xref $yref $zref $nset
                fi
              fi
            done
          fi
            if (( $(echo "$kdx == ${#mach_vel[@]}-1" | bc -l) )); then
              if ! $multi_mesh_files && [[ $stgy = "WARM" ]]; then
              exit_jou >> SET-$nset
            fi
          fi

        done
      fi
    fi
  fi

done

  if $aoa_grid; then
    printf "\n%1s\n" "Grid_files: AOA_GRIDS "   | fold -sw 80 | tee -a infout
  else
    printf "\n%1s\n" "Grid_files: -"              | fold -sw 80 | tee -a infout
  fi

  # Print grid path or polar case path
  echo ""
  if $start_from_polar_case ; then
    printf "%1s\n" "Starting from polar case files:"
    #realpath ../../02-RUNS/$polar_dir/$cas_link | fold -sw 80
    printf "%1s\n" "02-RUNS/$polar_dir/$cas_link" | fold -sw 80 | tee -a infout
    #realpath ../../02-RUNS/$polar_dir/$dat_link | fold -sw 80
    printf "%1s\n" "02-RUNS/$polar_dir/$dat_link" | fold -sw 80 | tee -a infout
  else
    #if $aoa_grid; then
    #  printf "\n%1s\n" "Grid_files: AOA_GRIDS "   | fold -sw 80 | tee -a infout
    #else
    #  printf "\n%1s\n" "Grid_files: -"              | fold -sw 80 | tee -a infout
    #fi
  for i in "${!grid[@]}"; do
      #realpath ${grid_dir[$i]}/${grid[$i]}.$ext | fold -sw 80 | tee -a infout
      printf "%1s\n" "${grid_dir[$i]}/${grid[$i]}.$ext" | sed "s%../../%%" | fold -sw 80 | tee -a infout
  done
  echo ""
fi
# Write to_run.sh file
echo "#!/bin/sh" > to_run.sh
job_name=()
if [[ $solv == "FLUENT" ]]; then
  solver_version="v261"

  if [[ $dim == "3d" ]]; then
    if $multi_mesh_files; then
      for i in "${!grid_param[@]}"; do
        if [[ $i -gt 0 ]]; then
          job_name+=("POLAR-${polr}_${acrt}_${grid_param[$i]}")
          echo "submit_fluent -i SET-${nset}_${grid_param[$i]} -n $ncpu -m 3ddp -v $solver_version -w $wtim -j ${job_name[$i-1]}" >> to_run.sh
        fi
      done
    elif [[ $stgy = "COLD" ]] && [[ ${#alpha_cl[@]} > 1 ]]; then
      for i in "${!alpha_cl[@]}"; do
        job_name+=("POLAR-${polr}_${acrt}_${alpha_cl[$i]}")
        echo "submit_fluent -i SET-${nset}_${alpha_cl[$i]} -n $ncpu -m 3ddp -v $solver_version -w $wtim -j ${job_name[$i]}" >> to_run.sh
      done
    elif [[ $stgy = "COLD" ]] && [[ ${#beta_cy[@]} > 1 ]]; then
      for i in "${!beta_cy[@]}"; do
        job_name+=("POLAR-${polr}_${acrt}_${beta_cy[$i]}")
        echo "submit_fluent -i SET-${nset}_${beta_cy[$i]} -n $ncpu -m 3ddp -v $solver_version -w $wtim -j ${job_name[$i]}" >> to_run.sh
      done
    else
      job_name+=("POLAR-${polr}_${acrt}")
      echo "submit_fluent -i SET-$nset -n $ncpu -m 3ddp -v $solver_version -w $wtim -j ${job_name[0]}" >> to_run.sh
    fi
  else
    if $multi_mesh_files; then
      for i in "${!grid_param[@]}"; do
        if [[ $i -gt 0 ]]; then
          job_name+=("POLAR-${polr}_${acrt}_${grid_param[$i]}")
          echo "submit_fluent -i SET-${nset}_${grid_param[$i]} -n $ncpu -m 2ddp -v $solver_version -w $wtim -j ${job_name[$i-1]}" >> to_run.sh
        fi
      done
    elif [[ $stgy = "COLD" ]] && [[ ${#alpha_cl[@]} > 1 ]]; then
      for i in "${!alpha_cl[@]}"; do
        job_name+=("POLAR-${polr}_${acrt}_${alpha_cl[$i]}")
        echo "submit_fluent -i SET-${nset}_${alpha_cl[$i]} -n $ncpu -m 2ddp -v $solver_version -w $wtim -j ${job_name[$i]}" >> to_run.sh
      done
    elif [[ $stgy = "COLD" ]] && [[ ${#beta_cy[@]} > 1 ]]; then
      for i in "${!beta_cy[@]}"; do
        job_name+=("POLAR-${polr}_${acrt}_${beta_cy[$i]}")
        echo "submit_fluent -i SET-${nset}_${beta_cy[$i]} -n $ncpu -m 2ddp -v $solver_version -w $wtim -j ${job_name[$i]}" >> to_run.sh
      done
    else
      job_name+=("POLAR-${polr}_${acrt}")
      echo "submit_fluent -i SET-$nset -n $ncpu -m 2ddp -v $solver_version -w $wtim -j ${job_name[0]}" >> to_run.sh
    fi
  fi

elif [[ $solv == "SU2" ]]; then
  echo "SU2 comando ..." >> to_run.sh
else
  printf "\e${RED}%1s\n\e${NC}" "Error: POLAR-$polr Parameter SOLVER: $solv  not found." | fold -sw 80
  exit 1
fi

for i in "${!job_name[@]}"; do
  printf "%-15s %-10s %-10s %-10s\n" "JOB_NAME: ${job_name[$i]}"  "SOLVER: $solv $solver_version" "CPU: $ncpu" "WTIME: $wtim" | fold -sw 80
done

chmod +x to_run.sh

if [[ $jamal_mode -eq 1 ]] || [[ $jamal_mode -eq 2 ]]; then
  echo ""
  echo -e "\033[38;5;226;5m.▄▄ · ▄• ▄▌▄▄▄▄· • ▌ ▄ ·. ▪  ▄▄▄▄▄   ▄▄·       • ▌ ▄ ·.  ▄▄▄· ▄▌  ▄▄▄ .▄▄▄▄▄▄▄▄ .\033[0m"
  echo -e "\033[38;5;226;5m▐█ ▀. █▪██▌▐█ ▀█▪·██ ▐███▪██ •██    ▐█ ▌▪ ▄█▀▄ ·██ ▐███▪▐█ ▄█ █•  ▀▄.▀·•██  ▀▄.▀·\033[0m"
  echo -e "\033[38;5;226;5m▄▀▀▀█▄█▌▐█▌▐█▀▀█▄▐█ ▌▐▌▐█·▐█· ▐█.▪  ██ ▄▄▐█▌.▐▌▐█ ▌▐▌▐█· ██▀· █ ▪ ▐▀▀▪▄ ▐█.▪▐▀▀▪▄\033[0m"
  echo -e "\033[38;5;226;5m▐█▄▪▐█▐█▄█▌██▄▪▐█ █ ██▌▐█▌▐█▌ ▐█▌·  ▐███▌▐█▌.▐▌██ ██▌▐█▌▐█▪·• █▌ ▄▐█▄▄▌ ▐█▌·▐█▄▄▌\033[0m"
  echo -e "\033[38;5;226;5m ▀▀▀▀  ▀▀▀ ·▀▀▀▀  ▀  █▪▀▀ ▀▀▀ ▀▀▀   ·▀▀▀  ▀█▄▀▪▀▀  █▪▀▀▀.▀    ▀▀▀  ▀▀▀  ▀▀▀  ▀▀▀ \033[0m"

  #printf "%-15s %-10s %-10s %-10s %-10s\n" "SOLVER: $solv" "REF: $nref" "SET: $nset" "CPU: $ncpu" "HPC: $nhpc" | fold -sw 80
  #printf "%-15s %-10s %-10s %-10s %-10s\n" "SOLVER: $solv $solver_version" "REF: $nref" "SET: $nset" "CPU: $ncpu" "WTIME: $wtim" | fold -sw 80
  #cat HPC-$nhpc | fold -sw 80
  echo ""
  # Replace polar run status to 0.
  sed -i "$line_number s/^\s*[0-9]\+/0/" ../../$matrix
  ./to_run.sh

fi

# Go back
cd ../../

if [[ $jamal_mode -eq 2 ]]; then
  monitor_and_postproc "POLAR-$polr" "02-RUNS/POLAR-${polr}/FLUENT_LOG" &
fi

line_number=$(awk "BEGIN {print $line_number + 1}")


# Align columns of matrix file.
column -t $matrix > temp
mv temp $matrix


