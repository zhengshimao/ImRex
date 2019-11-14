#! /usr/bin/env bash

OUTPUT_FILE=${1:-vdjdb-all-species-tra-trb-non-paired-summary.md}
VDJDB_FILE=${2:-vdjdb-all-species-tra-trb-non-paired.tsv}

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
if [ ! -f "$VDJDB_FILE" ]; then
        echo "The input file \"$VDJDB_FILE\" does not exist!"
        exit 1
fi

cat <<EOF > $OUTPUT_FILE

|Metric|Count|Command|
|---|---|---|
|Total number of records| $(tail -n +2 $VDJDB_FILE | wc -l)|\`tail -n +2 vdjdb-all-species-tra-trb-non-paired.tsv |  wc -l\`|
|TRA records|$(awk '$2 == "TRA" { print $3 }' $VDJDB_FILE | wc -l)|\`awk '$2 == "TRA" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | wc -l\`|
|TRB records|$(awk '$2 == "TRB" { print $3 }' $VDJDB_FILE | wc -l)|\`awk '$2 == "TRB" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | wc -l\`|
|Unique TRA sequences|$(awk '$2 == "TRA" { print $3 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRA" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique TRB sequences|$(awk '$2 == "TRB" { print $3 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRB" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique CDR3 sequences|$(tail -n +2 $VDJDB_FILE | cut -f3 | sort -u | wc -l)|\`tail -n +2 vdjdb-all-species-tra-trb-non-paired.tsv | cut -f3 | sort -u | wc -l\`|
|Unique epitope sequences|$(tail -n +2 $VDJDB_FILE | cut -f10 | sort -u | wc -l)|\`tail -n +2 vdjdb-all-species-tra-trb-non-paired.tsv | cut -f10 | sort -u | wc -l\`|
|Unique epitope sequences for TRA records|$(awk '$2 == "TRA" { print $10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRA" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique epitope sequences for TRB records|$(awk '$2 == "TRB" { print $10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRB" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique CDR3-epitope sequence pairs|$(tail -n +2 $VDJDB_FILE | cut -d $'\t' -f3,10 | sort -u | wc -l)|\`tail -n +2 vdjdb-all-species-tra-trb-non-paired.tsv | cut -d $'\t' -f3,10 | sort -u | wc -l\`|
|Unique TRA-CDR3-epitope sequence pairs|$(awk '$2 == "TRA" { print $3,$10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRA" { print $3,$10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique TRB-CDR3-epitope sequence pairs|$(awk '$2 == "TRB" { print $3,$10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRB" { print $3,$10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Number of epitope sequences shared between TRA and TRB records|$(comm -12 <(awk '$2 == "TRA" { print $10 }' $VDJDB_FILE | sort -u) <(awk '$2 == "TRB" { print $10 }' $VDJDB_FILE | sort -u) | wc -l)|\`comm -12 <(awk '$2 == "TRA" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) <(awk '$2 == "TRB" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) | wc -l\`|
|Number of CDR3 sequences shared between TRA and TRB records|$(comm -12 <(awk '$2 == "TRA" { print $3 }' $VDJDB_FILE | sort -u) <(awk '$2 == "TRB" { print $3 }' $VDJDB_FILE | sort -u) | wc -l)|\`comm -12 <(awk '$2 == "TRA" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) <(awk '$2 == "TRB" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) | wc -l\`|

**Human-only records**

|Metric|Count|Command|
|---|---|---|
|Total number of records|$(awk '$6 == "HomoSapiens" { print }' $VDJDB_FILE |  wc -l)|\`awk '$6 == "HomoSapiens" { print }' vdjdb-human-tra-trb-non-paired.tsv |  wc -l\`|
|TRA records|$(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $3 }' $VDJDB_FILE | wc -l)|\`awk '$2 == "TRA" && $6 == "HomoSapiens" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | wc -l\`|
|TRB records|$(awk '$2 == "TRB" && $6 == "HomoSapiens"  { print $3 }' $VDJDB_FILE | wc -l)|\`awk '$2 == "TRB" && $6 == "HomoSapiens"  { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | wc -l\`|
|Unique TRA sequences|$(awk '$2 == "TRA" && $6 == "HomoSapiens"  { print $3 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRA" && $6 == "HomoSapiens"  { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique TRB sequences|$(awk '$2 == "TRB" && $6 == "HomoSapiens"  { print $3 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRB" && $6 == "HomoSapiens"  { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique CDR3 sequences|$(awk '$6 == "HomoSapiens" { print }' $VDJDB_FILE | cut -f3 | sort -u | wc -l)|\`awk '$6 == "HomoSapiens" { print }' vdjdb-all-species-tra-trb-non-paired.tsv | cut -f3 | sort -u | wc -l\`|
|Unique epitope sequences|$(awk '$6 == "HomoSapiens" { print }' $VDJDB_FILE | cut -f10 | sort -u | wc -l)|\`awk '$6 == "HomoSapiens" { print }' vdjdb-all-species-tra-trb-non-paired.tsv | cut -f10 | sort -u | wc -l\`|
|Unique epitope sequences for TRA records|$(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRA" && $6 == "HomoSapiens" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique epitope sequences for TRB records|$(awk '$2 == "TRB" && $6 == "HomoSapiens" { print $10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRB" && $6 == "HomoSapiens" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique CDR3-epitope sequence pairs|$(awk '$6 == "HomoSapiens" { print }' $VDJDB_FILE | cut -d $'\t' -f3,10 | sort -u | wc -l)|\`awk '$6 == "HomoSapiens" { print }' vdjdb-all-species-tra-trb-non-paired.tsv | cut -d $'\t' -f3,10 | sort -u | wc -l\`|
|Unique TRA-CDR3-epitope sequence pairs|$(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $3,$10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRA" && $6 == "HomoSapiens" { print $3,$10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Unique TRB-CDR3-epitope sequence pairs|$(awk '$2 == "TRB" && $6 == "HomoSapiens" { print $3,$10 }' $VDJDB_FILE | sort -u | wc -l)|\`awk '$2 == "TRB" && $6 == "HomoSapiens" { print $3,$10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u | wc -l\`|
|Number of epitope sequences shared between TRA and TRB records|$(comm -12 <(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $10 }' $VDJDB_FILE | sort -u) <(awk '$2 == "TRB" && $6 == "HomoSapiens" { print $10 }' $VDJDB_FILE | sort -u) | wc -l)|\`comm -12 <(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) <(awk '$2 == "TRB" && $6 == "HomoSapiens" { print $10 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) | wc -l\`|
|Number of CDR3 sequences shared between TRA and TRB records|$(comm -12 <(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $3 }' $VDJDB_FILE | sort -u) <(awk '$2 == "TRB" && $6 == "HomoSapiens" { print $3 }' $VDJDB_FILE | sort -u) | wc -l)|\`comm -12 <(awk '$2 == "TRA" && $6 == "HomoSapiens" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) <(awk '$2 == "TRB" && $6 == "HomoSapiens" { print $3 }' vdjdb-all-species-tra-trb-non-paired.tsv | sort -u) | wc -l\`|

EOF
