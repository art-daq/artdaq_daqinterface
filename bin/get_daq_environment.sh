recorddir=$( awk '/record_directory/ { print $2} ' .settings )
recorddir=$( echo $( eval echo $recorddir ) )  # Expand environ variables in string     
