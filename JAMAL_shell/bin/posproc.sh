#!/bin/bash
: '
**********************************************************************************************
* Program name      : JAMAL - Job Automation and Management of Aerodynamic simuLations (CFD)
* Script            : posproc
*
* Author            : Maximiliano A. F. Souza
*
* Date created      : 20230301
*
* Purpose           : Post processing of the results
*
* Revision History  :
*
* Date        Author                      Rev.   Changes made
* 20230301    Maximiliano A. F. Souza     .1     Released beta version
*
**********************************************************************************************
'

# This function transforms the coordinates of a vector in wind axes
# to a vector in CFD body axes (x pointing backwards and z upwards) given alpha and beta angles.
wind2cfdbody() {
  # Degrees to radians.
  a=$(awk "BEGIN {printf \"%.10f\", $1*3.141592653589793/180.0}")
  b=$(awk "BEGIN {printf \"%.10f\", $2*3.141592653589793/180.0}")
  # Body forces and moments components.
  fxw=$(awk "BEGIN {printf \"%.10f\", $3}")
  fyw=$(awk "BEGIN {printf \"%.10f\", $4}")
  fzw=$(awk "BEGIN {printf \"%.10f\", $5}")
  mxw=$(awk "BEGIN {printf \"%.10f\", $6}")
  myw=$(awk "BEGIN {printf \"%.10f\", $7}")
  mzw=$(awk "BEGIN {printf \"%.10f\", $8}")
  coef=$9
  dim=${10}

  #echo >&2 $1
  #echo >&2 $2

  if [[ $dim == "3d" ]]; then
    if [[ $coef == "CDB" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fxw*cos($b)*cos($a) - $fyw*sin($b)*cos($a) - $fzw*sin($a)}")
    elif [[ $coef == "CYB" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fxw*sin($b) + $fyw*cos($b)}")
    elif [[ $coef == "CLB" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fxw*cos($b)*sin($a) - $fyw*sin($b)*sin($a) + $fzw*cos($a)}")
    elif [[ $coef == "CRB25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mxw*cos($b)*cos($a) - $myw*sin($b)*cos($a) - $mzw*sin($a)}")
    elif [[ $coef == "CMB25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mxw*sin($b) + $myw*cos($b)}")
    elif [[ $coef == "CNB25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mxw*cos($b)*sin($a) - $myw*sin($b)*sin($a) + $mzw*cos($a)}")
    fi
  else
  # Fluent 2D uses plane XY so the pitch moment is about Z axis.
    if [[ $coef == "CDB" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fxw*cos($a) - $fyw*sin($a)}")
    elif [[ $coef == "CYB" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fxw*sin($a) + $fyw*cos($a)}")
    elif [[ $coef == "CLB" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    0.0}")
    elif [[ $coef == "CRB25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    0.0}")
    elif [[ $coef == "CMB25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    0.0}")
    elif [[ $coef == "CNB25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mzw}")
    fi
  fi
  echo "$value"
}


# This function transforms the coordinates of a vector in body axes
# to a vector in wind axes given alpha and beta angles.
body2wind() {
  # Degrees to radians.
  a=$(awk "BEGIN {printf \"%.10f\", $1*3.141592653589793/180.0}")
  b=$(awk "BEGIN {printf \"%.10f\", $2*3.141592653589793/180.0}")
  # Body forces and moments components.
  # This function operates under the assumption that the bodys axes are
  # oriented with the X-axis pointing forward and the Z-axis pointing downward.
  fx=$(awk "BEGIN {printf \"%.10f\", $3}")
  fy=$(awk "BEGIN {printf \"%.10f\", $4}")
  fz=$(awk "BEGIN {printf \"%.10f\", $5}")
  mx=$(awk "BEGIN {printf \"%.10f\", $6}")
  my=$(awk "BEGIN {printf \"%.10f\", $7}")
  mz=$(awk "BEGIN {printf \"%.10f\", $8}")
  coef=$9
  dim=${10}

  #echo >&2 $1
  #echo >&2 $2

  if [[ $dim == "3d" ]]; then
    if [[ $coef == "CDW" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fx*cos($b)*cos($a) + $fy*sin($b) + $fz*cos($b)*sin($a)}")
      # The convention for the body axis is that the X direction points forward and the Z direction points downward.
      # Consequently, this orientation results in negative drag and lift values. To maintain intuitive interpretations
      # and common sense, these values are multiplied by -1.
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CYW" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$fx*sin($b)*cos($a) + $fy*cos($b) - $fz*sin($b)*sin($a)}")
    elif [[ $coef == "CLW" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$fx*sin($a) + $fz*cos($a)}")
      # The convention for the body axis is that the X direction points forward and the Z direction points downward.
      # Consequently, this orientation results in negative drag and lift values. To maintain intuitive interpretations
      # and common sense, these values are multiplied by -1.
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CRW25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mx*cos($b)*cos($a) + $my*sin($b) + $mz*cos($b)*sin($a)}")
    elif [[ $coef == "CMW25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$mx*sin($b)*cos($a) + $my*cos($b) - $mz*sin($b)*sin($a)}")
    elif [[ $coef == "CNW25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$mx*sin($a) + $mz*cos($a)}")
    fi
  else
  # Fluent 2D uses plane XY so the pitch moment is about Z axis.
    if [[ $coef == "CDW" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fx*cos($a) + $fy*sin($a)}")
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CYW" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$fx*sin($a) + $fy*cos($a)}")
    elif [[ $coef == "CLW" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    0.0}")
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CRW25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    0.0}")
    elif [[ $coef == "CMW25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    0.0}")
    elif [[ $coef == "CNW25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mz}")
    fi
  fi
  echo "$value"
}

# This function transforms the coordinates of a vector in body axes
# to a vector in stability axes given alph and beta angles.
body2stab() {
  # Degrees to radians.
  a=$(awk "BEGIN {printf \"%.10f\", $1*3.141592653589793/180.0}")
  b=$(awk "BEGIN {printf \"%.10f\", $2*3.141592653589793/180.0}")
  # Body forces and moments components.
  # This function operates under the assumption that the bodys axes are
  # oriented with the X-axis pointing forward and the Z-axis pointing downward.
  fx=$(awk "BEGIN {printf \"%.10f\", $3}")
  fy=$(awk "BEGIN {printf \"%.10f\", $4}")
  fz=$(awk "BEGIN {printf \"%.10f\", $5}")
  mx=$(awk "BEGIN {printf \"%.10f\", $6}")
  my=$(awk "BEGIN {printf \"%.10f\", $7}")
  mz=$(awk "BEGIN {printf \"%.10f\", $8}")
  coef=$9
  dim=${10}

  if [[ $dim == "3d" ]]; then
    if   [[ $coef == "CDS" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fx*cos($a) + $fz*sin($a)}")
      # The convention for the body axis is that the X direction points forward and the Z direction points downward.
      # Consequently, this orientation results in negative drag and lift values. To maintain intuitive interpretations
      # and common sense, these values are multiplied by -1.
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CYS" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fy}")
    elif [[ $coef == "CLS" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$fx*sin($a) + $fz*cos($a)}")
      # The convention for the body axis is that the X direction points forward and the Z direction points downward.
      # Consequently, this orientation results in negative drag and lift values. To maintain intuitive interpretations
      # and common sense, these values are multiplied by -1.
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CRS25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mx*cos($a) + $mz*sin($a)}")
    elif [[ $coef == "CMS25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $my}")
    elif [[ $coef == "CNS25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$mx*sin($a) + $mz*cos($a)}")
    fi
  else
    if   [[ $coef == "CDS" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fx*cos($a) + $fz*sin($a)}")
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CYS" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $fy}")
    elif [[ $coef == "CLS" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$fx*sin($a) + $fz*cos($a)}")
      value=$(awk "BEGIN {printf \"%.10f\", -1*$value}")
    elif [[ $coef == "CRS25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $mx*cos($a) + $mz*sin($a)}")
    elif [[ $coef == "CMS25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\",    $my}")
    elif [[ $coef == "CNS25" ]]; then
      value=$(awk "BEGIN {printf \"%.10f\", -1*$mx*sin($a) + $mz*cos($a)}")
    fi
  fi
  echo "$value"
}

# This function takes a string of numbers and a number to search for
find_index() {
  local list="$1"   # store the string of numbers as a variable
  local num=$2      # store the number to search for as a variable
  local index=-1    # initialize the index to -1
  # Convert the string into an array using awk
  local arr=($(awk -v list="$list" 'BEGIN {print list}'))
  # Loop through the array and check each element
  for i in "${!arr[@]}"; do
    if awk -v num="$num" -v elem="${arr[$i]}" 'BEGIN {exit !(num == elem)}'; then
      index=$i   # store the index of the matching element
      break     # exit the loop early
    fi
  done
  echo $index   # output the index
}

# This function check if it is a number
is_number() {
  if [[ "$1" =~ ^[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][-+]?[0-9]+)?$ ]]; then
    return 0
  else
    return 1
  fi
}

BLACK='\033[0;30m'
RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
LGRAY='\033[0;37m'
DGRAY='\033[1;30m'
LRED='\033[1;31m'
LGREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color


posopt=$1
polars=($2)
acr_comps=($3)
phi_plane=$4
flag=$5
if [[ $flag == 1 ]];then
  stations_plane=($6)
  start_point_plane=0
  end_point_plane=0
  steps_plane=0
else
  stations_plane=0
  start_point_plane=$6
  end_point_plane=$7
  steps_plane=$8
fi

# Print help menu
if [[ $posopt == "-h" ]] || [[ $posopt == "--help" ]]; then
  echo ""
  printf "\e${YELLOW}%1s\n\n\e${NC}" "        YALLA JAMAL POSPROC 1.0 beta (2023 Dec)" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "Usage: posproc.sh option polars" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "Option 1 to generate adf files" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "Option 2 to generate flowvis files" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "Option 4 to generate spanwise load distribution and chordwise Cp distribution" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "Option 8 to generate probe files" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "To initiate the execution of either all options simultaneously or specifically select two options, enter the total count of the desired choices. For example, if you wish to generate both ADF and Flowvis files, you should input the value 3. Or if you want ADF and probe files you should input 9. Or 15 for everything at once, and so on. " | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "Example 1: Generate adf files for one polar" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "posproc.sh 1 POLAR-001" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "or for more the one polar" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "posproc.sh 1 \"POLAR-001 POLAR-002\"" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "Example 2: Generate load and Cp distribution files" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "posproc.sh 4 \"POLAR-001 POLAR-002\" \"WING FLAP\" 0 2 -1.2 -4.3 20" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "posproc.sh 4 \"POLAR-001 POLAR-002\" \"WING FLAP\" 0 1 \"-1.2 -1.8 -2.5 -3.0 -3.5 -4.0 -4.3\" "
  exit 1
fi


if ! is_number $posopt; then
  echo ""
  printf "\e${RED}%1s\n\e${NC}" "Error: First argument is an option flag and it must be a number." | fold -sw 80
  printf "\e${RED}%1s\n\e${NC}" "Option 1 to generate adf files" | fold -sw 80
  printf "\e${RED}%1s\n\e${NC}" "Option 2 to generate flowvis files" | fold -sw 80
  printf "\e${RED}%1s\n\e${NC}" "Option 4 to generate span load distribution" | fold -sw 80
  printf "\e${RED}%1s\n\n\e${NC}" "Option 8 to generate probe files" | fold -sw 80
  printf "\e${RED}%1s\n\n\e${NC}" "To initiate the execution of either all options simultaneously or specifically select two options, enter the total count of the desired choices. For example, if you wish to generate both ADF and Flowvis files, you should input the value 3. Or if you want ADF and probe files you should input 9. Or 15 for everything at once, and so on. " | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "Usage: posproc.sh option polars" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "Example 1: Generate adf files for one polar" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "posproc.sh 1 POLAR-001" | fold -sw 80
  printf "\e${LGRAY}%1s\n\e${NC}" "or for more the one polar" | fold -sw 80
  printf "\e${LGRAY}%1s\n\n\e${NC}" "posproc.sh 1 \"POLAR-001 POLAR-002\"" | fold -sw 80
  exit 1
fi


bin=$(echo "obase=2; ibase=10; $posopt"|bc)
padbin=$(printf "%04d" ${bin})


for polar in "${polars[@]}"; do
  run_dir="02-RUNS/$polar"

  # if the directory doesn't exist, skip to next polar
  if [[ ! -d "$run_dir" ]]; then
    echo "Warning: Directory $run_dir not found. Skipping this POLAR." >&2
    continue
  fi

  #cd 02-RUNS/$polar
  cd "$run_dir" || { echo "Failed to cd into $run_dir" >&2; continue; }
  dirpath=$(pwd)
  echo $dirpath
 
  meshlog_file=()
  for i in meshlog*; do meshlog_file+=($i); done 

  # if the meshlog file doesn't exist, skip to next polar
  if [[ ! -f "${meshlog_file[0]}" ]]; then
    echo "Warning: Meshlog file $run_dir/${meshlog_file[0]} not found. Skipping this POLAR." >&2
    cd ../../
    continue
  fi

  # Read mesh log and find the line containing the Dimension
  matched_line=$(grep -m 1 "Dimension: " "${meshlog_file[0]}")
  dim=$(echo "$matched_line" | awk -F "Dimension: " '{print tolower($2)}' | awk '{gsub(/^[^[:alnum:]]+|[^[:alnum:]]+$/, ""); print}')

  # if the infout file doesn't exist, skip to next polar
  if [[ ! -f "infout" ]]; then
    echo "Warning: Posproc input file $run_dir/infout not found. Skipping this POLAR." >&2
    cd ../../
    continue
  fi
  dos2unix infout

  # Loop through each line of the infout file
  keys=()
  values=()
  zonekeys=()
  zones=0
  cases=0
  case1=0
  while read -r line; do
    # Ignore empty or whitespace-only lines.
    if [[ "$line" =~ ^[[:space:]]*$ ]]; then
      continue
    fi
    # Remove non-ASCII characters from each line.
    line=$(echo "$line" | tr -cd '[:print:][:cntrl:]\n')

    if [[ $line != "" ]]; then
      line=`sed "s/:/: /g" <<<"$line"`
      list1=($line)
      if [[ $line == *":"* ]]; then
        pids=""
        alpha=""
        beta=""
        name=""
        list2=($(echo "$line" | awk '{for(i=1;i<=NF;i++) {if($i ~ /.*:/) {gsub(/:/,"",$i); printf "%s ", $i":"}}}'))
        keys+=($(echo "$line" | awk '{for(i=1;i<=NF;i++) {if($i ~ /.*:/) {gsub(/:/,"",$i); printf "%s ", $i}}}'))
        if [[ $zones == 1 ]]; then zonekeys+=($(echo "$line" | awk '{for(i=1;i<=NF;i++) {if($i ~ /.*:/) {gsub(/:/,"",$i); printf "%s ", $i}}}')); fi

        for item in "${list1[@]}"; do
          if [[ ! "${list2[@]}" =~ (^|[[:space:]])"${item}"($|[[:space:]]) ]]; then
            if [[ $zones == 0 ]]; then
              values+=("$item")
            else
              pids+=",${item}"
            fi
          fi
        done
        if [[ ! -z $pids ]]; then
          values+=("$pids")
        fi

      elif [[ $line == *"[CASES]"* ]]; then
        zones=0
        cases=1
      elif [[ $zones == 1 ]]; then
        linec=$(echo $line | tr ' ' ',')
        last_index=$(( ${#values[@]} - 1 ))
        values[$last_index]="${values[$last_index]},$linec"
      elif [[ $line == *"[ZONES]"* ]]; then
        zones=1
      elif [[ $cases == 1 ]]; then
        if is_number ${list1[1]}; then
          if [[ $case1 == 0 ]]; then
            for item in "${list1[@]}"; do
              values+=("$item")
            done
            case1=1
          else
            casen="${list1[0]}"
            machs="${list1[1]}"
            reyns="${list1[2]}"
            alpha="${list1[3]}"
            beta="${list1[4]}"
            name="${list1[5]}"
            niter="${list1[6]}"
            last7_index=$(( ${#values[@]} - 7 ))
            last6_index=$(( ${#values[@]} - 6 ))
            last5_index=$(( ${#values[@]} - 5 ))
            last4_index=$(( ${#values[@]} - 4 ))
            last3_index=$(( ${#values[@]} - 3 ))
            last2_index=$(( ${#values[@]} - 2 ))
            last1_index=$(( ${#values[@]} - 1 ))
            values[$last7_index]="${values[$last7_index]},$casen"
            values[$last6_index]="${values[$last6_index]},$machs"
            values[$last5_index]="${values[$last5_index]},$reyns"
            values[$last4_index]="${values[$last4_index]},$alpha"
            values[$last3_index]="${values[$last3_index]},$beta"
            values[$last2_index]="${values[$last2_index]},$name"
            values[$last1_index]="${values[$last1_index]},$niter"
          fi
        else
          for item in "${list1[@]}"; do
            keys+=("$item")
          done
        fi
      fi
    fi
  done < "infout"
  #for item in "${zonekeys[@]}"; do
  #  echo $item
  #done
  # Split keys and values into arrays
  IFS=" " read -ra key_array <<< "${keys[@]}"
  IFS=" " read -ra value_array <<< "${values[@]}"

  # Create dictionary-like structure
  declare -A dict=()
  for i in "${!key_array[@]}"; do
    dict[${key_array[$i]}]=${value_array[$i]}
  done

  IFS="," read -r -a WALL <<< "${dict["WALL"]}"
  IFS="," read -r -a WING <<< "${dict["WING"]}"
  IFS="," read -r -a NOWING <<< "${dict["NOWING"]}"
  IFS="," read -r -a BODY <<< "${dict["BODY"]}"
  IFS="," read -r -a NOBODY <<< "${dict["NOBODY"]}"
  IFS="," read -r -a VTAIL <<< "${dict["VTAIL"]}"
  IFS="," read -r -a NOVTAIL <<< "${dict["NOVTAIL"]}"
  IFS="," read -r -a HTAIL <<< "${dict["HTAIL"]}"
  IFS="," read -r -a NOHTAIL <<< "${dict["NOHTAIL"]}"
  IFS="," read -r -a FLAP <<< "${dict["FLAP"]}"
  IFS="," read -r -a NOFLAP <<< "${dict["NOFLAP"]}"
  IFS="," read -r -a FARFIELD <<< "${dict["FARFIELD"]}"
  IFS="," read -r -a SYMMETRY <<< "${dict["SYMMETRY"]}"
  IFS="," read -r -a INLET_FAN <<< "${dict["INLET_FAN"]}"
  IFS="," read -r -a OUTLET_COLD <<< "${dict["OUTLET_COLD"]}"
  IFS="," read -r -a OUTLET_HOT <<< "${dict["OUTLET_HOT"]}"
  IFS="," read -r -a MACH_NUMBER <<< "${dict["MACH"]}"
  IFS="," read -r -a REYNOLDS_NUMBER <<< "${dict["REYNOLDS"]}"
  IFS="," read -r -a ALPHA <<< "${dict["ALPHA"]}"
  IFS="," read -r -a CLS <<< "${dict["CLS"]}"
  IFS="," read -r -a CYS <<< "${dict["CYS"]}"
  IFS="," read -r -a BETA <<< "${dict["BETA"]}"
  IFS="," read -r -a NAME <<< "${dict["NAME"]}"

  #for key in ${!dict[@]}; do
  #  echo $key ${dict["$key"]}
  #done
  #exit 1

  # Create dictionary-like structure for zones
  declare -A zone_dict=()
  declare -a zone_keys=()
  for i in "${!key_array[@]}"; do
    if [[ "${key_array[$i]}" == "WALL" ]] || [[ "${key_array[$i]}" == "WING" ]] || [[ "${key_array[$i]}" == "NOWING" ]] || [[ "${key_array[$i]}" == "BODY" ]] || [[ "${key_array[$i]}" == "NOBODY" ]] || [[ "${key_array[$i]}" == "VTAIL" ]] || [[ "${key_array[$i]}" == "NOVTAIL" ]] || [[ "${key_array[$i]}" == "HTAIL" ]] || [[ "${key_array[$i]}" == "NOHTAIL" ]] || [[ "${key_array[$i]}" == "BLADES" ]] || [[ "${key_array[$i]}" == "NOBLADES" ]] || [[ "${key_array[$i]}" == "FLAP" ]] || [[ "${key_array[$i]}" == "NOFLAP" ]]; then
      if [[ "${dict["${key_array[$i]}"]}" != ",-" ]]; then
        zone_keys+=("${key_array[$i]}")
        zone_dict["${key_array[$i]}"]=${dict["${key_array[$i]}"]}
      fi
    fi
  done

  sym=1
  for i in "${SYMMETRY[@]}"; do
    if [[ $i == "-" ]]; then
      sym=0
    fi
  done

  aoa_grid=${dict["Grid_files"]}
  Mach=${dict["Mach"]}
  Rey=${dict["Reynolds"]}
  hpft=${dict["HP[ft]"]}
  rho=${dict["rho[kg/m3]"]}
  psta=${dict["p[Pa]"]}
  ptot=${dict["ptot[Pa]"]}
  qimp=${dict["qimp[Pa]"]}
  Tsta=${dict["T[K]"]}
  Ttot=${dict["Ttot[K]"]}
  vel=${dict["V[m/s]"]}
  ssp=${dict["a[m/s]"]}
  qdin=${dict["qdin[Pa]"]}
  Sref=${dict["SREF[m2]"]}
  if [[ $sym == 1 ]]; then
    Area=$(awk "BEGIN { printf \"%10.3f\", $Sref/2.0  }")
  else
    Area=$Sref
  fi
  Bref=${dict["BREF[m]"]}
  Cref=${dict["CREF[m]"]}
  Xref=${dict["XREF[m]"]}
  Yref=${dict["YREF[m]"]}
  Zref=${dict["ZREF[m]"]}
  ACRF=${dict["AIRCRAFT"]}
  CONF=${dict["CONFIGURATION"]}
  ELV1=${dict["ELV1"]}
  ELV2=${dict["ELV2"]}
  ELV3=${dict["ELV3"]}
  ELV4=${dict["ELV4"]}
  RUD1=${dict["RUD1"]}
  RUD2=${dict["RUD2"]}
  RUD3=${dict["RUD3"]}
  RUD4=${dict["RUD4"]}
  AIL1=${dict["AIL1"]}
  AIL2=${dict["AIL2"]}
  AIL3=${dict["AIL3"]}
  AIL4=${dict["AIL4"]}
  FLP1=${dict["FLP1"]}
  FLP2=${dict["FLP2"]}
  FLP3=${dict["FLP3"]}
  FLP4=${dict["FLP4"]}
  if [[ $ELV1 == "-" ]]; then ELV1="0"; fi
  if [[ $ELV2 == "-" ]]; then ELV2="0"; fi
  if [[ $ELV3 == "-" ]]; then ELV3="0"; fi
  if [[ $ELV4 == "-" ]]; then ELV4="0"; fi
  if [[ $RUD1 == "-" ]]; then RUD1="0"; fi
  if [[ $RUD2 == "-" ]]; then RUD2="0"; fi
  if [[ $RUD3 == "-" ]]; then RUD3="0"; fi
  if [[ $RUD4 == "-" ]]; then RUD4="0"; fi
  if [[ $AIL1 == "-" ]]; then AIL1="0"; fi
  if [[ $AIL2 == "-" ]]; then AIL2="0"; fi
  if [[ $AIL3 == "-" ]]; then AIL3="0"; fi
  if [[ $AIL4 == "-" ]]; then AIL4="0"; fi
  if [[ $FLP1 == "-" ]]; then FLP1="0"; fi
  if [[ $FLP2 == "-" ]]; then FLP2="0"; fi
  if [[ $FLP3 == "-" ]]; then FLP3="0"; fi
  if [[ $FLP4 == "-" ]]; then FLP4="0"; fi



  # Generate ADF
  if [[ ${padbin:3:1} == 1  ]]; then

    alpha_sweep=false
    for i in "${ALPHA[@]}"; do
      if [[ "${ALPHA[0]}" != "$i" ]]; then
        alpha_sweep=true
        break
      fi
    done
    # No need for sorting when there is only one case.
    if [[ "${#ALPHA[@]}" = "1" ]]; then
      alpha_sweep=true
    fi

    cl_sweep=false
    for i in "${CLS[@]}"; do
      if [[ "${CLS[0]}" != "$i" ]]; then
        cl_sweep=true
        break
      fi
    done
    # No need for sorting when there is only one case.
    if [[ "${#CLS[@]}" = "1" ]]; then
      cl_sweep=true
    fi

    beta_sweep=false
    for i in "${BETA[@]}"; do
      if [[ "${BETA[0]}" != "$i" ]]; then
        beta_sweep=true
        break
      fi
    done
    # No need for sorting when there is only one case.
    if [[ "${#BETA[@]}" = "1" ]]; then
      if $cl_sweep || $alpha_sweep; then 
        beta_sweep=false
      else
        beta_sweep=true
      fi
    fi

    cy_sweep=false
    for i in "${CYS[@]}"; do
      if [[ "${CYS[0]}" != "$i" ]]; then
        cy_sweep=true
        break
      fi
    done
    # No need for sorting when there is only one case.
    if [[ "${#CYS[@]}" = "1" ]]; then
      if $cl_sweep || $alpha_sweep; then
        cy_sweep=false
      else
        cy_sweep=true
      fi
    fi
 
    mach_sweep=false
    for i in "${MACH_NUMBER[@]}"; do
      if [[ "${MACH_NUMBER[0]}" != "$i" ]]; then
        mach_sweep=true
        break
      fi
    done

    sorted_list=()
    # Sort the list based on ALPHA.
    if $alpha_sweep ; then
      sorted_list=($(for item in "${ALPHA[@]}"; do echo "$item"; done | sort -n | cut -d " " -f 2-))
      sorted_list_index=($(for item in "${sorted_list[@]}"; do echo $(find_index "${ALPHA[*]}" "$item"); done))
    fi
    #echo ***********************
    #echo alpha_sweep $alpha_sweep
    #echo beta_sweep  $beta_sweep
    #echo cl_sweep $cl_sweep
    #echo cy_sweep $cy_sweep
    #echo *************************
    # Sort the list based on CLS.
    if $cl_sweep ; then
      ALPHA=()
      while read line; do
        IFS=" " read -r -a albeout <<< "$line"
        ALPHA+=(${albeout[3]})
      done < <(tail -n +2 albe.out)
      sorted_list=($(for item in "${CLS[@]}"; do echo "$item"; done | sort -n | cut -d " " -f 2-))
      sorted_list_index=($(for item in "${sorted_list[@]}"; do echo $(find_index "${CLS[*]}" "$item"); done))
    fi

    # Sort the list based on CYS.
    if $cy_sweep ; then
      BETA=()
      while read line; do
        IFS=" " read -r -a albeout <<< "$line"
        BETA+=(${albeout[3]})
      done < <(tail -n +2 albe.out)
      sorted_list=($(for item in "${CYS[@]}"; do echo "$item"; done | sort -n | cut -d " " -f 2-))
      sorted_list_index=($(for item in "${sorted_list[@]}"; do echo $(find_index "${CYS[*]}" "$item"); done))
    fi

    # Sort the list based on MACH.
    if $mach_sweep ; then
      sorted_list=($(for item in "${MACH_NUMBER[@]}"; do echo "$item"; done | sort -n | cut -d " " -f 2-))
      sorted_list_index=($(for item in "${sorted_list[@]}"; do echo $(find_index "${MACH_NUMBER[*]}" "$item"); done))
    fi

    # Sort the list based on BETA.
    if $beta_sweep ; then
      sorted_list=($(for item in "${BETA[@]}"; do echo "$item"; done | sort -n | cut -d " " -f 2-))
      sorted_list_index=($(for item in "${sorted_list[@]}"; do echo $(find_index "${BETA[*]}" "$item"); done))
    fi

    for key in "${zone_keys[@]}"; do
      IFS="," read -r -a ZONE_LIST <<< "${zone_dict["$key"]}"
      if [[ "$key" == "WALL" ]]; then
        adf_file_name=$polar.adf
        printf "\n%81s\n" "========================= INTEGRATING ALL WALL SURFACES =========================="
      else
        printf "\n%81s\n" "========================= INTEGRATING $key SURFACES =========================="
        adf_file_name=${polar}_$key.adf
      fi

      now=`date`
      printf "%-10s %-10s %-10s %-10s %-10s %-1s"\
      "AIRCRAFT:" "$ACRF" "CONFIG.: " "$CONF" "WALLS: " "${ZONE_LIST[*]:1}"                 | tee $adf_file_name
      printf "\n%-10s %3s\n"\
      "POLAR:" "${dict["POLAR"]}"                                                           | tee -a $adf_file_name
      printf "%s\n" "$now"                                                                  | tee -a $adf_file_name
      printf "%s\n" 32                                                                      | tee -a $adf_file_name
      printf "%12s %12s %12s %12s %12s %12s %12s %12s\n%12s %12s %12s %12s %12s %12s %12s %12s\n"\
      "SREF" "CREF" "BREF" "XREF" "YREF" "ZREF" "MNOM" "RNOM"\
      "HPFT" "PSTA" "PTOT" "QDIN" "QIMP" "TSTA" "TTOT" "RHO"                                | tee -a $adf_file_name
      printf "%12s %12s %12s %12s %12s %12s %12s %12s\n%12s %12s %12s %12s %12s %12s %12s %12s\n"\
      "ELV1" "ELV2" "ELV3" "ELV4" "RUD1" "RUD2" "RUD3" "RUD4"\
      "AIL1" "AIL2" "AIL3" "AIL4" "FLP1" "FLP2" "FLP3" "FLP4"                               | tee -a $adf_file_name
      printf "%12.3f %12.3f %12.3f %12.3f %12.3f %12.3f %12.3f %12.3E\n%12.0f %12.3f %12.3f %12.3f %12.3f %12.3f %12.3f %12.3f\n"\
      "$Sref" "$Cref" "$Bref" "$Xref" "$Yref" "$Zref" "$Mach" "$Rey"\
      "$hpft" "$psta" "$ptot" "$qdin" "$qimp" "$Tsta" "$Ttot" "$rho"                        | tee -a $adf_file_name
      printf "%12.0f %12.0f %12.0f %12.0f %12.0f %12.0f %12.0f %12.0f\n%12.0f %12.0f %12.0f %12.0f %12.0f %12.0f %12.0f %12.0f\n"\
      "$ELV1" "$ELV2" "$ELV3" "$ELV4" "$RUD1" "$RUD2" "$RUD3" "$RUD4"\
      "$AIL1" "$AIL2" "$AIL3" "$AIL4" "$FLP1" "$FLP2" "$FLP3" "$FLP4"                       | tee -a $adf_file_name
     #printf "%12s " "${ZONE_LIST[@]:1}"                                     | fold -sw 104 | tee -a $adf_file_name
      printf "%s\n" 22                                                                      | tee -a $adf_file_name
      printf "%10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s %10s\n"\
      "MACH" "REYNOLDS" "ALPHA" "BETA" "CDB" "CYB" "CLB" "CRB25" "CMB25" "CNB25" "CDS" "CYS" "CLS" "CRS25" "CMS25" "CNS25" "CDW" "CYW" "CLW" "CRW25" "CMW25" "CNW25" | tee -a $adf_file_name

      for i in "${sorted_list_index[@]}"; do

        # FORCE
        # Initialize variables to hold the net total forces for each direction
        fox=0
        foy=0
        foz=0

        # Loop over each line in the table, up to the pattern ---
        while read line && [[ "$line" != "---"* ]]; do
          # Split the line into fields using whitespace as the delimiter
          fields=($line)
          # Extract the zone name from the line
          PID=$(echo "${fields[0]}" | sed 's/[()]//g')
          if [[ " ${ZONE_LIST[*]} " =~ " ${PID} " ]]; then
            # Extract the x, y, and z pressure forces from the line
            press_force_x=$(echo "${fields[1]}" | sed 's/[()]//g')
            press_force_y=$(echo "${fields[2]}" | sed 's/[()]//g')
            press_force_z=$(echo "${fields[3]}" | sed 's/[()]//g')
            # Extract the x, y, and z friction forces from the line
            frict_force_x=$(echo "${fields[4]}" | sed 's/[()]//g')
            frict_force_y=$(echo "${fields[5]}" | sed 's/[()]//g')
            frict_force_z=$(echo "${fields[6]}" | sed 's/[()]//g')
            # Extract the x, y, and z total forces from the line
            total_force_x=$(echo "${fields[7]}" | sed 's/[()]//g')
            total_force_y=$(echo "${fields[8]}" | sed 's/[()]//g')
            total_force_z=$(echo "${fields[9]}" | sed 's/[()]//g')
            # Add the forces to the net totals
            fox=$(awk "BEGIN { printf \"%.10f\", $fox + $total_force_x}")
            foy=$(awk "BEGIN { printf \"%.10f\", $foy + $total_force_y}")
            foz=$(awk "BEGIN { printf \"%.10f\", $foz + $total_force_z}")
          fi
        done < <(tail -n +6 FORCE_${NAME[$i]}.out | grep -v "^#")


        #if [[ $sym == 1 ]]; then
        #  foy=$(awk "BEGIN { printf \"%.10f\", 0}")
        #fi

        #if [[ $aoa_grid = "AOA_GRIDS" ]]; then
        #  # Total Drag coefficient in the wind axis.
        #  CDW=$(awk "BEGIN { printf \"%.10f\", $fox/($qdin*$Area)}")
        #  # Total Y Force coefficient in the wind axis.
        #  CYW=$(awk "BEGIN { printf \"%.10f\", $foy/($qdin*$Area)}")
        #  # Total Lift coefficient in the wind axis.
        #  CLW=$(awk "BEGIN { printf \"%.10f\", $foz/($qdin*$Area)}")

        #  # Converting the forces from wind axis to CFD body axis (x pointing backwards and z upwards).

        #  # Total Drag coefficient in the CFD body axis (x pointing backwards and z upwards).
        #  CDB=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CDB" $dim)
        #  # Total X Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
        #  CXB=$(awk "BEGIN { printf \"%.10f\", -1*$CDB }")
	#  # Total Y Force coefficient in the CFD and aircraft body axis (X pointing forward and Z downwards).
        #  CYB=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CYB" $dim)
	#  # Total Lift coefficient in the CFD body axis (X pointing backwards and Z upwards).
        #  CLB=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CLB" $dim)
	#  # Total Z Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
        #  CZB=$(awk "BEGIN { printf \"%.10f\", -1*$CLB }")

	#else

        #  # Total Drag coefficient in the CFD body axis (x pointing backwards and z upwards).
        #  CDB=$(awk "BEGIN { printf \"%.10f\", $fox/($qdin*$Area)}")
        #  # Total X Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
        #  CXB=$(awk "BEGIN { printf \"%.10f\", -1*$CDB }")
        #  # Total Y Force coefficient in the CFD and aircraft body axis (X pointing forward and Z downwards).
        #  CYB=$(awk "BEGIN { printf \"%.10f\", $foy/($qdin*$Area)}")
        #  # Total Lift coefficient in the CFD body axis (X pointing backwards and Z upwards).
        #  CLB=$(awk "BEGIN { printf \"%.10f\", $foz/($qdin*$Area)}")
        #  # Total Z Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
        #  CZB=$(awk "BEGIN { printf \"%.10f\", -1*$CLB }")
        #fi

        #echo $foz
        #echo $CLB
        #echo $qdin
        #echo $Area

        # MOMENT
        # Initialize variables to hold the net total moments for each direction
        mox=0
        moy=0
        moz=0

        # Loop over each line in the table, up to the pattern ---
        while read line && [[ "$line" != "---"* ]]; do
          # Split the line into fields using whitespace as the delimiter
          fields=($line)
          # Extract the zone name from the line
          PID=$(echo "${fields[0]}" | sed 's/[()]//g')
          if [[ " ${ZONE_LIST[*]} " =~ " ${PID} " ]]; then
            # Extract the x, y, and z pressure moments from the line
            press_moment_x=$(echo "${fields[1]}" | sed 's/[()]//g')
            press_moment_y=$(echo "${fields[2]}" | sed 's/[()]//g')
            press_moment_z=$(echo "${fields[3]}" | sed 's/[()]//g')
            # Extract the x, y, and z friction moments from the line
            frict_moment_x=$(echo "${fields[4]}" | sed 's/[()]//g')
            frict_moment_y=$(echo "${fields[5]}" | sed 's/[()]//g')
            frict_moment_z=$(echo "${fields[6]}" | sed 's/[()]//g')
            # Extract the x, y, and z total moments from the line
            total_moment_x=$(echo "${fields[7]}" | sed 's/[()]//g')
            total_moment_y=$(echo "${fields[8]}" | sed 's/[()]//g')
            total_moment_z=$(echo "${fields[9]}" | sed 's/[()]//g')
            # Add the moments to the net totals
            mox=$(awk "BEGIN { printf \"%.10f\", $mox + $total_moment_x}")
            moy=$(awk "BEGIN { printf \"%.10f\", $moy + $total_moment_y}")
            moz=$(awk "BEGIN { printf \"%.10f\", $moz + $total_moment_z}")
          fi
        done < <(tail -n +6 MOMENT_${NAME[$i]}.out | grep -v "^#")

        #if [[ $sym == 1 ]]; then
        #  mox=$(awk "BEGIN { printf \"%.10f\", 0}")
        #  moz=$(awk "BEGIN { printf \"%.10f\", 0}")
        #fi

        matched_line=$(grep -m 1 "Moments - Moment Center" "MOMENT_${NAME[$i]}.out")
        moment_center_point=($(echo $matched_line | cut -d "(" -f2 | cut -d ")" -f1))
        XMON=${moment_center_point[0]}
        YMON=${moment_center_point[1]}
        ZMON=${moment_center_point[2]}

        rx=$(awk "BEGIN { printf \"%.10f\", $XMON - $Xref}")
        ry=$(awk "BEGIN { printf \"%.10f\", $YMON - $Yref}")
        rz=$(awk "BEGIN { printf \"%.10f\", $ZMON - $Zref}")

        mox=$(awk "BEGIN { printf \"%.10f\", $mox + $ry*$foz - $rz*$foy}")
        moy=$(awk "BEGIN { printf \"%.10f\", $moy + $rz*$fox - $rx*$foz}")
        moz=$(awk "BEGIN { printf \"%.10f\", $moz + $rx*$foy - $ry*$fox}")


        if [[ $aoa_grid = "AOA_GRIDS" ]]; then
	  # Total Drag coefficient in the wind axis.
          CDW=$(awk "BEGIN { printf \"%.10f\", $fox/($qdin*$Area)}")
          # Total Y Force coefficient in the wind axis.
          CYW=$(awk "BEGIN { printf \"%.10f\", $foy/($qdin*$Area)}")
          # Total Lift coefficient in the wind axis.
          CLW=$(awk "BEGIN { printf \"%.10f\", $foz/($qdin*$Area)}")

	  # Total roll moment coefficient in the wind axis.
          CRW25=$(awk "BEGIN { printf \"%.10f\", $mox/($qdin*$Area*$Bref)}")
          # Total pitch moment coefficient in the wind axis.
          CMW25=$(awk "BEGIN { printf \"%.10f\", $moy/($qdin*$Area*$Cref)}")
          # Fluent 2D uses plane XY, so the pitch moment is about Z axis.
          if [[ $dim == "3d" ]]; then
            # Total yaw moment coefficient in the wind axis.
            CNW25=$(awk "BEGIN { printf \"%.10f\", $moz/($qdin*$Area*$Bref)}")
          else
            # If 2D, pitch moment is about Z axis.
            CNW25=$(awk "BEGIN { printf \"%.10f\", $moz/($qdin*$Area*$Cref)}")
          fi

          # Converting the forces from wind axis to CFD body axis (x pointing backwards and z upwards).

          # Total Drag coefficient in the CFD body axis (x pointing backwards and z upwards).
          CDB=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CDB" $dim)
          # Total X Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
          CXB=$(awk "BEGIN { printf \"%.10f\", -1*$CDB }")
          # Total Y Force coefficient in the CFD and aircraft body axis (X pointing forward and Z downwards).
          CYB=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CYB" $dim)
          # Total Lift coefficient in the CFD body axis (X pointing backwards and Z upwards).
          CLB=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CLB" $dim)
          # Total Z Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
          CZB=$(awk "BEGIN { printf \"%.10f\", -1*$CLB }")

          # Converting the moments from wind axis to CFD body axis (x pointing backwards and z upwards).

          # Total roll moment coefficient in the CFD body axis (X pointing backwards and z upwards).
          CRBc25=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CRB25" $dim)
          # Total roll moment coefficient in the aircraft body axis (X pointing forward and Z downwards).
          CRB25=$(awk "BEGIN { printf \"%.10f\", -1*$CRBc25 }")
          # Total pitch moment coefficient in the CFD and aircraft body axis (X pointing forwards and Z downwards).
          CMB25=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CMB25" $dim)
          # Total yaw moment coefficient in the CFD body axis (X pointing backwards and z upwards).
          CNBc25=$(wind2cfdbody "${ALPHA[$i]}" "${BETA[$i]}" $CDW $CYW $CLW $CRW25 $CMW25 $CNW25 "CNB25" $dim)
          # Total yaw moment coefficient in the aircraft body axis (X pointing forwards and Z downwards).
          CNB25=$(awk "BEGIN { printf \"%.10f\", -1*$CNBc25 }")

        else

	  # Total Drag coefficient in the CFD body axis (x pointing backwards and z upwards).
          CDB=$(awk "BEGIN { printf \"%.10f\", $fox/($qdin*$Area)}")
          # Total X Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
          CXB=$(awk "BEGIN { printf \"%.10f\", -1*$CDB }")
          # Total Y Force coefficient in the CFD and aircraft body axis (X pointing forward and Z downwards).
          CYB=$(awk "BEGIN { printf \"%.10f\", $foy/($qdin*$Area)}")
          # Total Lift coefficient in the CFD body axis (X pointing backwards and Z upwards).
          CLB=$(awk "BEGIN { printf \"%.10f\", $foz/($qdin*$Area)}")
          # Total Z Force coefficient in the aircraft body axis (X pointing forward and Z downwards).
          CZB=$(awk "BEGIN { printf \"%.10f\", -1*$CLB }")

          # Total roll moment coefficient in the aircraft body axis (X pointing forwards and Z downwards).
          CRB25=$(awk "BEGIN { printf \"%.10f\", -1*$mox/($qdin*$Area*$Bref)}")
          # Total pitch moment coefficient in the aircraft body axis (X pointing forwards and Z downwards).
          CMB25=$(awk "BEGIN { printf \"%.10f\", $moy/($qdin*$Area*$Cref)}")
          # Fluent 2D uses plane XY, so the pitch moment is about Z axis.
          if [[ $dim == "3d" ]]; then
            # Total yaw moment coefficient in the aircraft body axis (X pointing forwards and Z downwards).
            CNB25=$(awk "BEGIN { printf \"%.10f\", -1*$moz/($qdin*$Area*$Bref)}")
          else
            # If 2D, pitch moment is about Z axis.
            CNB25=$(awk "BEGIN { printf \"%.10f\", $moz/($qdin*$Area*$Cref)}")
          fi
        fi

        # Converting the forces and moments from body axis to stability axis.
        # The body axis must be oriented with the X-axis pointing forward and the Z-axis pointing downward.
        CDS=$(body2stab "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CDS" $dim)
        CYS=$(body2stab "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CYS" $dim)
        CLS=$(body2stab "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CLS" $dim)
        CRS25=$(body2stab "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CRS25" $dim)
        CMS25=$(body2stab "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CMS25" $dim)
        CNS25=$(body2stab "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CNS25" $dim)

        # Converting the forces and moments from body axis to wind axis.
        # The body axis must be oriented with the X-axis pointing forward and the Z-axis pointing downward.
        CDW=$(body2wind "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CDW" $dim)
        CYW=$(body2wind "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CYW" $dim)
        CLW=$(body2wind "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CLW" $dim)
        CRW25=$(body2wind "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CRW25" $dim)
        CMW25=$(body2wind "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CMW25" $dim)
        CNW25=$(body2wind "${ALPHA[$i]}" "${BETA[$i]}" $CXB $CYB $CZB $CRB25 $CMB25 $CNB25 "CNW25" $dim)

        #echo ""
        #echo ""
        printf "%10.3f %10.3E %10.3f %10.3f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f %10.6f\n"\
        "${MACH_NUMBER[$i]}" "${REYNOLDS_NUMBER[$i]}" "${ALPHA[$i]}" "${BETA[$i]}" "$CDB" "$CYB" "$CLB" "$CRB25" "$CMB25" "$CNB25" "$CDS" "$CYS" "$CLS" "$CRS25" "$CMS25" "$CNS25" "$CDW" "$CYW" "$CLW" "$CRW25" "$CMW25" "$CNW25" | tee -a $adf_file_name

      done

      if [[ "$key" == "WALL"  ]]; then
        mkdir -p ../../03-RESULTS/ADF
        mv $adf_file_name ../../03-RESULTS/ADF/.
        echo
        echo $adf_file_name has been successfully generated and stored in the 03-RESULTS/ADF directory.
        echo
      else
        #mkdir -p ../../03-RESULTS/ADF/ADF_COMP/$polar
        mkdir -p ../../03-RESULTS/ADF/ADF_COMP
        #mv $adf_file_name ../../03-RESULTS/ADF/ADF_COMP/$polar/.
        mv $adf_file_name ../../03-RESULTS/ADF/ADF_COMP/.
        echo
        echo $adf_file_name has been successfully generated and stored in the 03-RESULTS/ADF/ADF_COMP/$polar directory.
        echo
      fi

    done
  fi

  # Generate Flowvis
  if [[ ${padbin:2:1} == 1 ]]; then
    if [ -e ../../00-SUPPORT/flowvis.ses ]; then
      cp ../../00-SUPPORT/flowvis.ses .
    else
      echo file flowvis.ses not found in 00-SUPPORT
      exit 1
    fi

    alpha_sweep=false
    for i in "${ALPHA[@]}"; do
      if [[ "${ALPHA[0]}" != "$i" ]]; then
        alpha_sweep=true
        break
      fi
    done
    
    cl_sweep=false
    for i in "${CLS[@]}"; do
      if [[ "${CLS[0]}" != "$i" ]]; then
        cl_sweep=true
        break
      fi
    done
    
    beta_sweep=false
    for i in "${BETA[@]}"; do
      if [[ "${BETA[0]}" != "$i" ]]; then
        beta_sweep=true
        break
      fi
    done
    
    cy_sweep=false
    for i in "${CYS[@]}"; do
      if [[ "${CYS[0]}" != "$i" ]]; then
        cy_sweep=true
        break
      fi
    done
    
    mach_sweep=false
    for i in "${MACH_NUMBER[@]}"; do
      if [[ "${MACH_NUMBER[0]}" != "$i" ]]; then
        mach_sweep=true
        break
      fi
    done

    # Determine max index
    if $alpha_sweep; then max_index=$(( ${#ALPHA[@]} - 1 )); sweep_name="AoA"; sweep_arr=( "${ALPHA[@]}" ); format_value="0f";
    elif $cl_sweep; then max_index=$(( ${#CLS[@]} - 1 )); sweep_name="CLS"; sweep_arr=( "${CLS[@]}" ); format_value="2f";
    elif $beta_sweep; then max_index=$(( ${#BETA[@]} - 1 )); sweep_name="Beta"; sweep_arr=( "${BETA[@]}" ); format_value="0f";
    elif $cy_sweep; then max_index=$(( ${#CYS[@]} - 1 )); sweep_name="CYS"; sweep_arr=( "${CYS[@]}" ); format_value="2f";
    elif $mach_sweep; then max_index=$(( ${#MACH_NUMBER[@]} - 1 )); sweep_name="Mach"; sweep_arr=( "${MACH[@]}" ); format_value="2f";
    fi    
    
    max_states=$(( max_index + 1 ))

    # Loop from 0 up to max, but prepend each i so that the lowest i runs last
    for (( idx = max_index; idx >= 0; idx-- )); do
      state=$(( idx + 1 ))
      if awk "BEGIN { exit !(${sweep_arr[idx]} >= 0) }"; then
	    sweep_value=$(awk "BEGIN { printf \"%.${format_value}\", ${sweep_arr[idx]} }")
        sed -i '/%states_title%/a\
0:option state '"$state"'\
0:state usertitle enable '"$state"'\
0:state usertitle set "'${polar}':'${sweep_name}''$sweep_value'" '"$state" flowvis.ses
      fi
    done
    sed -i '/%states_title%/d' flowvis.ses

sed -i '/%mach_function%/a\
function create setlabel Mach\
function create loopscalar 1,'"$max_states"',1 "" "1" "s\\${i}.sf[label={Velocity,Magnitude}]/%sound_speed%"' flowvis.ses
sed -i '/%mach_function%/d' flowvis.ses

# Loop from 0 up to max, but prepend each i so that the lowest i runs last
    for (( idx = max_index; idx >= 0; idx-- )); do
      state=$(( idx + 1 ))
      if awk "BEGIN { exit !(${sweep_arr[idx]} >= 0) }"; then
        sed -i '/%mach_function_states%/a\
0:options state "Time nearest 0.000000000000000 AND State = '"$state"'"\
function scalar label 0 "Mach"' flowvis.ses
      fi
    done
sed -i '/%mach_function_states%/d' flowvis.ses


sed -i '/%ptot_function%/a\
function create setlabel Ptot\
function create loopscalar 1,'"$max_states"',1 "" "1" "s\\${i}.sf[label={Pressure}]*pow(1+0.2*pow(s\\${i}.sf[label={Mach}],2),3.5)"' flowvis.ses
sed -i '/%ptot_function%/d' flowvis.ses

# Loop from 0 up to max, but prepend each i so that the lowest i runs last
    for (( idx = max_index; idx >= 0; idx-- )); do
      state=$(( idx + 1 ))
      if awk "BEGIN { exit !(${sweep_arr[idx]} >= 0) }"; then
        sed -i '/%ptot_function_states%/a\
0:options state "Time nearest 0.000000000000000 AND State = '"$state"'"\
function scalar label 0 "Ptot"' flowvis.ses
      fi
    done
sed -i '/%ptot_function_states%/d' flowvis.ses


sed -i '/%ptot_ratio_function%/a\
function create setlabel Ptot_ratio\
function create loopscalar 1,'"$max_states"',1 "" "1" "s\\${i}.sf[label={Ptot}]/%p_tot_res%"' flowvis.ses
sed -i '/%ptot_ratio_function%/d' flowvis.ses

# Loop from 0 up to max, but prepend each i so that the lowest i runs last
    for (( idx = max_index; idx >= 0; idx-- )); do
      state=$(( idx + 1 ))
      if awk "BEGIN { exit !(${sweep_arr[idx]} >= 0) }"; then
        sed -i '/%ptot_ratio_function_states%/a\
0:options state "Time nearest 0.000000000000000 AND State = '"$state"'"\
function scalar label 0 "Ptot_ratio"' flowvis.ses
      fi
    done
sed -i '/%ptot_ratio_function_states%/d' flowvis.ses


    dos2unix flowvis.ses
    
    #p_tot_res=$(awk -v v="$ptot" 'BEGIN {x = v * 1.0; r = int(x + 0.5); printf("%d.0\n", r) }')
    #p_stat=$(awk -v v="$psta" 'BEGIN {x = v; r = int(x + 0.5); printf("%d.0\n", r) }')
    #velocity=$(awk -v v="$vel" 'BEGIN {x = v; r = int(x + 0.5); printf("%d.0\n", r) }')
    #sound_speed=$(awk -v v="$ssp" 'BEGIN {x = v; r = int(x + 0.5); printf("%d.0\n", r) }')
    p_tot_res=$(awk -v v="$ptot" 'BEGIN {printf "%.3f\n", v}')
    p_stat=$(awk -v v="$psta" 'BEGIN {printf "%.3f\n", v}')
    velocity=$(awk -v v="$vel" 'BEGIN {printf "%.3f\n", v}')
    sound_speed=$(awk -v v="$ssp" 'BEGIN {printf "%.3f\n", v}')
    ptot_ratio_min=$(awk -v s="$psta" -v t="$ptot" 'BEGIN {printf "%.3f\n", s/t}')
    ptot_ratio_isosurf=$(awk -v m="$ptot_ratio_min" 'BEGIN {printf "%.3f\n", 1.0 - 2.0*(1.0 - m)/20}')

    if [[ $sym == 1 ]]; then
      clone_new_ymirror="explode model clone new ymirror"
      disable_clone="explode model clone disable all"
      enable_clone="explode model clone enable all"
    else
      clone_new_ymirror=""
      disable_clone=""
      enable_clone=""
    fi

    sed -i s!%dirpath%!$dirpath!g flowvis.ses
    sed -i s!%polar%!$polar!g flowvis.ses
    sed -i s!%case0%!${NAME[0]}!g flowvis.ses
    sed -i s!%p_tot_res%!$p_tot_res!g flowvis.ses
    sed -i s!%ptot_ratio_min%!$ptot_ratio_min!g flowvis.ses
    sed -i s!%ptot_ratio_isosurf%!$ptot_ratio_isosurf!g flowvis.ses
    sed -i s!%p_stat%!$p_stat!g flowvis.ses
    sed -i s!%velocity%!$velocity!g flowvis.ses
    sed -i s!%sound_speed%!$sound_speed!g flowvis.ses
    sed -i s!%mach_inf%!$Mach!g flowvis.ses
    sed -i s!%max_states%!$max_states!g flowvis.ses
    sed -i s!%clone_new_ymirror%!"${clone_new_ymirror}"!g flowvis.ses
    sed -i s!%disable_clone%!"$disable_clone"!g flowvis.ses
    sed -i s!%enable_clone%!"$enable_clone"!g flowvis.ses

    #meta=/lustre1/home/halcon/JGRAVES/BETACAE/ANSA_2216/BETA_CAE_Systems/meta_post_v22.1.6/meta_post64.sh
    #$meta -virtualx_64bit -changedir $dirpath --session-id -b -e -s $dirpath/flowvis.ses $dirpath
    ml metapost/24.1.1
    meta_post64.sh -virtualx_64bit -changedir $dirpath --session-id -b -e -s $dirpath/flowvis.ses $dirpath
    mkdir -p ../../03-RESULTS/FLOWVIS/$polar
    mv *.gif ../../03-RESULTS/FLOWVIS/$polar/.
  fi

  # Generate load distribution
  if [[ ${padbin:1:1} == 1 ]]; then
    for acr_comp in ${acr_comps[@]}; do    
      echo cl and cp distribution
      if [ -e ../../00-SUPPORT/distclcp_meta.py ]; then
        cp ../../00-SUPPORT/distclcp_meta.py .
      else
        echo file distclcp_meta.py not found in 00-SUPPORT
	exit 1
      fi
      
      for key in "${zone_keys[@]}"; do
        if [[ "$key" == "$acr_comp" ]]; then
          sed -i s/%CLCP_PIDS%/${zone_dict["$key"]:1}/g distclcp_meta.py
        fi
      done
      
      sed -i s!%dirpath%!$dirpath!g distclcp_meta.py
      sed -i s/%filename%/${NAME[0]}/g distclcp_meta.py
      sed -i s/%aoa%/${ALPHA[0]}/g distclcp_meta.py
      sed -i s/%phi_plane%/$phi_plane/g distclcp_meta.py
      sed -i s/%flag%/$flag/g distclcp_meta.py
      sed -i s/%start_point_plane%/$start_point_plane/g distclcp_meta.py
      sed -i s/%end_point_plane%/$end_point_plane/g distclcp_meta.py
      sed -i s/%steps_plane%/$steps_plane/g distclcp_meta.py
      sed -i s/%stations_plane%/"${stations_plane[*]}"/g distclcp_meta.py
      
      ml metapost/24.1.1
      meta_post64.sh -virtualx_64bit -changedir $dirpath --session-id -b -e -s $dirpath/distclcp_meta.py $dirpath

      mkdir -p ../../03-RESULTS/DISTCLCP/$polar/$acr_comp
      mv cp_dist_state* ../../03-RESULTS/DISTCLCP/$polar/$acr_comp/.
      mv section_state* ../../03-RESULTS/DISTCLCP/$polar/$acr_comp/.
      mv total_force_state* ../../03-RESULTS/DISTCLCP/$polar/$acr_comp/.
    done
  fi

  # Generate Probe results
  if [[ ${padbin:0:1} == 1 ]]; then
    for i in "${!NAME[@]}"; do
      echo $dirpath
      if [ -e ../../00-SUPPORT/extract_alpha_beta_3.py ]; then
        cp ../../00-SUPPORT/extract_alpha_beta_3.py .
      else
        echo file extract_alpha_beta_3.py not found in 00-SUPPORT
        exit 1
      fi
      if [ -e ../../00-SUPPORT/probe_coords_1.dat ]; then
        cp ../../00-SUPPORT/probe_coords_1.dat .
      else
        echo file probe_coords_1.dat not found in 00-SUPPORT
        exit 1
      fi

      sed -i s/%filename%/${NAME[$i]}/g extract_alpha_beta_3.py
      sed -i s/%aoa%/${ALPHA[$i]}/g extract_alpha_beta_3.py
      #meta=/lustre1/home/halcon/JGRAVES/BETACAE/ANSA_2216/BETA_CAE_Systems/meta_post_v22.1.6/meta_post64.sh
      #$meta -virtualx_64bit -changedir $dirpath --session-id -b -e -s $dirpath/extract_alpha_beta_3.py $dirpath
      ml metapost/22.1.6
      meta_post64.sh -virtualx_64bit -changedir $dirpath --session-id -b -e -s $dirpath/extract_alpha_beta_3.py $dirpath
    done
    mkdir -p ../../03-RESULTS/PROBE/$polar
    mv probe_results* ../../03-RESULTS/PROBE/$polar/.
  fi

  cd ../../

done
