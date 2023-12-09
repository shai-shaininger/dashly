#!/bin/bash

# Host and port to send the JSON data
host="234.0.0.1"
port="10005"

# Number of fields in the JSON object
n=50
start_time=$(date +%s.%N)

while true; do 
end_time=$(date +%s.%N)
running_time=$(echo "$end_time - $start_time" | bc)

# Generate a JSON object with random numbers
json_data="[{\"title\":\"my_title\",\"fields\":{\"timetag\":$running_time,"
for ((i=1; i<=n; i++)); do
    field_name="field_$i"
    random_number=$(((i * 20) + RANDOM % 20))  # Adjust the range as needed
    json_data+="\"$field_name\":$random_number"
    if [ $i -lt $n ]; then
        json_data+=","
    fi
done
json_data+="}}]"

# Send the JSON data using netcat
echo "$json_data" | nc -u -w0 "$host" "$port"
# echo "$json_data"

sleep 0.1
done

exit
