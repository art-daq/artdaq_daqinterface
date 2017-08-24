recorddir=$( awk '/record_directory/ { print $2} ' $DAQINTERFACE_SETTINGS )
recorddir=$( echo $( eval echo $recorddir ) )  # Expand environ variables in string     
