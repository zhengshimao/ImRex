#! /usr/bin/env bash

OUTPUT_FILE=${1:-vdjdb-browser-summary.md}
VDJDB_FILE=${2:-vdjdb-browser.tsv}

# check if output file already exists and confirm before overwriting
if [ -f "$OUTPUT_FILE" ]; then
    read -r -p "The file \"$OUTPUT_FILE\" already exists; overwrite it? [y/N] " response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
    then
        echo "Aborting without writing output..."
        exit 1
    fi
fi

# check if input file exists
if [ ! -f "${VDJDB_FILE}" ]; then
        echo "The input file \"${VDJDB_FILE}\" does not exist!"
        exit 1
fi

cat <<EOF > $OUTPUT_FILE

| Metric                                                         | Count                                                                                                                                    | Command                                                                                                                       |
|----------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| Total number of records                                        | $(tail -n +2 ${VDJDB_FILE} | wc -l)                                                                                                        | \`tail -n +2 ${VDJDB_FILE}  |  wc -l\`                                                                                                 |
| TRA records                                                    | $(awk '$1 == "TRA" { print $2 }' ${VDJDB_FILE} | wc -l)                                                                                    | \`awk '\$1 == "TRA" { print \$2 }' ${VDJDB_FILE} | wc -l\`                                                                             |
| TRB records                                                    | $(awk '$1 == "TRB" { print $2 }' ${VDJDB_FILE} | wc -l)                                                                                    | \`awk '\$1 == "TRB" { print \$2 }' ${VDJDB_FILE} | wc -l\`                                                                             |
| Unique TRA sequences                                           | $(awk '$1 == "TRA" { print $2 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                          | \`awk '\$1 == "TRA" { print \$2 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                   |
| Unique TRB sequences                                           | $(awk '$1 == "TRB" { print $2 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                          | \`awk '\$1 == "TRB" { print \$2 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                   |
| Unique CDR3 sequences                                          | $(tail -n +2 ${VDJDB_FILE} | cut -f2 | sort -u | wc -l)                                                                                    | \`tail -n +2 ${VDJDB_FILE} | cut -f2 | sort -u | wc -l\`                                                                               |
| Unique epitope sequences                                       | $(tail -n +2 ${VDJDB_FILE} | cut -f4 | sort -u | wc -l)                                                                                    | \`tail -n +2 ${VDJDB_FILE} | cut -f4 | sort -u | wc -l\`                                                                              |
| Unique epitope sequences for TRA records                       | $(awk '$1 == "TRA" { print $4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                          | \`awk '\$1 == "TRA" { print \$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                  |
| Unique epitope sequences for TRB records                       | $(awk '$1 == "TRB" { print $4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                          | \`awk '\$1 == "TRB" { print \$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                  |
| Unique CDR3-epitope sequence pairs                             | $(tail -n +2 ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | wc -l)                                                                         | \`tail -n +2 ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | wc -l\`                                                                   |
| Unique TRA-CDR3-epitope sequence pairs                         | $(awk '$1 == "TRA" { print $2,$4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                       | \`awk '\$1 == "TRA" { print $2,$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                |
| Unique TRB-CDR3-epitope sequence pairs                         | $(awk '$1 == "TRB" { print $2,$4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                       | \`awk '\$1 == "TRB" { print $2,$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                |
| Number of epitope sequences shared between TRA and TRB records | $(comm -12 <(awk '$1 == "TRA" { print $4 }' ${VDJDB_FILE} | sort -u) <(awk '$1 == "TRB" { print $4 }' ${VDJDB_FILE} | sort -u) | wc -l)      | \`comm -12 <(awk '\$1 == "TRA" { print \$4 }' ${VDJDB_FILE} | sort -u) <(awk '\$1 == "TRB" { print \$4 }' ${VDJDB_FILE} | sort -u) | wc -l\`  |
| Number of CDR3 sequences shared between TRA and TRB records    | $(comm -12 <(awk '$1 == "TRA" { print $2 }' ${VDJDB_FILE} | sort -u) <(awk '$1 == "TRB" { print $2 }' ${VDJDB_FILE} | sort -u) | wc -l)      | \`comm -12 <(awk '\$1 == "TRA" { print \$2 }' ${VDJDB_FILE} | sort -u) <(awk '\$1 == "TRB" { print \$2 }' ${VDJDB_FILE} | sort -u) | wc -l\`    |
| Epitope distribution for the unique CDR3-epitope pairs         |                                 | \`tail -n +2 ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | cut -f2 | sort | uniq -c | sort -nr | head -20\`                                  |

$(tail -n +2 ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | cut -f2 | sort | uniq -c | sort -nr | head -20)

**Human-only records**

| Metric                                                             | Count                                                                                                                                                                        | Command                                                                                                                                                                             |
|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|   Total number of records                                          | $(awk '$3 == "HomoSapiens" { print }' ${VDJDB_FILE} |  wc -l)                                                                                                                  | \`awk '\$3 == "HomoSapiens" { print }' ${VDJDB_FILE} |  wc -l\`                                                                                                                              |
|   TRA records                                                      | $(awk '$1 == "TRA" && $3 == "HomoSapiens" { print $2 }' ${VDJDB_FILE} | wc -l)                                                                                                 | \`awk '\$1 == "TRA" && \$3 == "HomoSapiens"  { print \$2 }' ${VDJDB_FILE} | wc -l\`                                                                                                          |
|   TRB records                                                      | $(awk '$1 == "TRB" && $3 == "HomoSapiens"  { print $2 }' ${VDJDB_FILE} | wc -l)                                                                                                | \`awk '\$1 == "TRB" && \$3 == "HomoSapiens"  { print \$2 }' ${VDJDB_FILE} | wc -l\`                                                                                                          |
|   Unique TRA sequences                                             | $(awk '$1 == "TRA" && $3 == "HomoSapiens"  { print $2 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                                      | \`awk '\$1 == "TRA" && \$3 == "HomoSapiens"  { print \$2 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                                                |
|   Unique TRB sequences                                             | $(awk '$1 == "TRB" && $3 == "HomoSapiens"  { print $2 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                                      | \`awk '\$1 == "TRB" && \$3 == "HomoSapiens"  { print \$2 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                                                |
|   Unique CDR3 sequences                                            | $(awk '$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -f2 | sort -u | wc -l)                                                                                               | \`awk '\$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -f2 | sort -u | wc -l\`                                                                                                           |
|   Unique epitope sequences                                         | $(awk '$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -f4 | sort -u | wc -l)                                                                                              | \`awk '\$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -f4 | sort -u | wc -l\`                                                                                                          |
|   Unique epitope sequences for TRA records                         | $(awk '$1 == "TRA" && $3 == "HomoSapiens" { print $4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                                      | \`awk '\$1 == "TRA" && \$3 == "HomoSapiens" { print \$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                                                |
|   Unique epitope sequences for TRB records                         | $(awk '$1 == "TRB" && $3 == "HomoSapiens" { print $4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                                      | \`awk '\$1 == "TRB" && \$3 == "HomoSapiens" { print \$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                                                |
|   Unique CDR3-epitope sequence pairs                               | $(awk '$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | wc -l)                                                                                   | \`awk '\$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | wc -l\`                                                                                               |
|   Unique TRA-CDR3-epitope sequence pairs                           | $(awk '$1 == "TRA" && $3 == "HomoSapiens" { print $2,$4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                                   | \`awk '\$1 == "TRA" && \$3 == "HomoSapiens" { print \$2,\$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                                            |
|   Unique TRB-CDR3-epitope sequence pairs                           | $(awk '$1 == "TRB" && $3 == "HomoSapiens" { print $2,$4 }' ${VDJDB_FILE} | sort -u | wc -l)                                                                                   | \`awk '\$1 == "TRB" && \$3 == "HomoSapiens" { print \$2,\$4 }' ${VDJDB_FILE} | sort -u | wc -l\`                                                                                            |
|   Number of epitope sequences shared between TRA and TRB records   | $(comm -12 <(awk '$1 == "TRA" && $3 == "HomoSapiens" { print $4 }' ${VDJDB_FILE} | sort -u) <(awk '$1 == "TRB" && $3 == "HomoSapiens" { print $4 }' ${VDJDB_FILE} | sort -u)   | wc -l)|\`comm -12 <(awk '\$1 == "TRA" && \$3 == "HomoSapiens" { print \$4 }' ${VDJDB_FILE} | sort -u) <(awk '\$1 == "TRB" && \$3 == "HomoSapiens" { print \$4 }' ${VDJDB_FILE} | sort -u) | wc -l\` |
|   Number of CDR3 sequences shared between TRA and TRB records      | $(comm -12 <(awk '$1 == "TRA" && $3 == "HomoSapiens" { print $2 }' ${VDJDB_FILE} | sort -u) <(awk '$1 == "TRB" && $3 == "HomoSapiens" { print $2 }' ${VDJDB_FILE} | sort -u)     | wc -l)|\`comm -12 <(awk '\$1 == "TRA" && \$3 == "HomoSapiens" { print \$2 }' ${VDJDB_FILE} | sort -u) <(awk '\$1 == "TRB" && \$3 == "HomoSapiens" { print \$2 }' ${VDJDB_FILE} | sort -u) | wc -l\`   |
|   Epitope distribution for the unique CDR3-epitope pairs           |                             | \`awk '\$6 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -d $'\t' -f3,10 | sort -u | cut -f2 | sort | uniq -c | sort -nr | head -20\`                                                                 |

$(awk '$3 == "HomoSapiens" { print }' ${VDJDB_FILE} | cut -d $'\t' -f2,4 | sort -u | cut -f2 | sort | uniq -c | sort -nr | head -20)

EOF
