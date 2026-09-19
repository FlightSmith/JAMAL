#!/bin/bash

# Directory where the output files will be stored
output_dir="output_files"

# Create the output directory if it doesn't exist
mkdir -p "$output_dir"

# Check if at least one file is provided
if [ "$#" -eq 0 ]; then
    echo "No files specified. Please provide the file names as arguments."
    exit 1
fi

dir=$(pwd)
dir_output=$dir/$output_dir
cd 03-RESULTS/ADF


# Initialize an associative array to hold lines
declare -A aero_lines
header=""

# Loop over each file provided as an argument
for polar in "$@"; do

    input_file=${polar}.adf

    # Check if the file exists
    if [ ! -f "$input_file" ]; then
        echo "File $input_file does not exist. Skipping."
        continue
    fi

    # Initialize variables
    in_aero_section=false
    line_counter=0
    polar_value=""

    # Read the input file line by line
    while IFS= read -r line; do
        # Extract the Polar value
        if [[ "$line" =~ ^POLAR: ]]; then
            polar_value=$(echo "$line" | awk '{print $2}')
        fi

        # Capture the header of the aerodynamic data section
        if [[ "$line" =~ ^[[:space:]]*MACH ]]; then
            header="POLAR $line"
            in_aero_section=true
            continue
        fi

        # If we're in the aerodynamic section, collect all lines
        if $in_aero_section; then
            if [[ "$line" =~ ^[[:space:]]*[0-9]+\.[0-9]+ ]]; then
                ((line_counter++))
                # Prepend the Polar value to the line and append it to the corresponding entry in the associative array
                aero_lines[$line_counter]+="$polar_value    $line"$'\n'
            fi
        fi
    done < "$input_file"
    
    echo "Processed $input_file with Polar value $polar_value."
done

# Write the header and each line to the corresponding output file
for line_number in "${!aero_lines[@]}"; do
    output_file="${dir_output}/output_line_$line_number.txt"
    echo "$header" > "$output_file"
    echo "${aero_lines[$line_number]}" >> "$output_file"
    echo "Created $output_file with data from line $line_number."
done

echo "Extraction complete. Check the output files in the directory: $output_dir"

