"use strict";
/*globals $ */

/*$(function() {
    $(function($) {
      $('#jclock').jclock({ utc: true,
                            format: '%A, %B %d, %Y %H:%M:%S UTC' });
    });
});*/

$(function($) {
    var optionsCST = {
	utc: true,
	utc_offset: -5,
	format: 'Local Time: %A, %B %d, %Y %H:%M:%S Central'
    }
    $('#jclock2').jclock(optionsCST);
    
    var optionsUTC = {
	utc: true,
	format: '%A, %B %d, %Y %H:%M:%S UTC (plot time)'
    }
    $('#jclock').jclock(optionsUTC);

});
