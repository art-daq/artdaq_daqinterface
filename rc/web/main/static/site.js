function update_fetcher(url, period_arg, success_fn, datatype) {
    var fetch_interval;
    var period = period_arg || 1000; // msec
    function interval_fn() {
        clearInterval(fetch_interval);
        $.ajax({url: url,
                dataType: datatype || "json"})
            .done(function(data) {
                      success_fn(data);
                      fetch_interval = setInterval(interval_fn, period);
                  })
            .fail(function(data) {
                      console.log("FAIL", data);
                      fetch_interval = setInterval(interval_fn, period);
                  });
    }
    fetch_interval = setInterval(interval_fn, period);
}



var charth1; // global
$(function() {
    charth1 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph-h1',
		events: {load: requestDatah1}
	       },
	title: {text: 'ArtDAQ Data Logger Event Rate'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Rate (Hz)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "Event Rate",data: []}
	]
    });
});

function requestDatah1() {
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/Data.Logger.Event.Rate',
	datatype: "json",
	success: function(data) {
	    charth1.series[0].setData(JSON.parse(data));
	    // call it again after 5 second
	    setTimeout(requestDatah1, 1000);
	},
	cache: false
    });
}
////////////////////////
var charth2; // global
$(function() {
    charth2 = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph-h2',
		events: {load: requestDatah2}
	       },
	title: {text: 'ArtDAQ EvetnBuilder Incomplete Event Counters'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: '',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "EventBuilder1",data: []},
	    {name: "EventBuilder2",data: []},
	    {name: "EventBuilder3",data: []},
	    {name: "EventBuilder4",data: []},
	    {name: "EventBuilder5",data: []},
	    {name: "EventBuilder6",data: []},
	    {name: "EventBuilder7",data: []},
	    {name: "EventBuilder8",data: []}
	    ]
    });
});

function requestDatah2() {
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.1.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[0].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.2.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[1].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.3.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[2].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.4.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[3].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.5.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[4].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.6.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[5].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.7.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[6].setData(JSON.parse(data));
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/RCReporter/EventBuilder.8.Incomplete.Event.Count',
	datatype: "json",
	success: function(data) {
	    charth2.series[7].setData(JSON.parse(data));
	    // call it again after 5 second
	    setTimeout(requestDatah2, 1000);
	},
	cache: false
    });
}




update_fetcher("/lbnerc/control/moni/", 1000, 
                function(data) {
                    $("#moni-values").html(data);
                }, "html");


update_fetcher("/lbnerc/components/", 1000,
	       function(data) {
		   $("#comp-states").html(data);
	       }, "html");

update_fetcher("/lbnerc/control/getcurrentrun", 1000,
	       function(data) {
		   $('#getcurrentrun').html(data);
	       }, "html");

update_fetcher("/lbnerc/control/getcurrentdbrun", 1000,
	       function(data) {
		   $('#getcurrentdbrun').html(data);
	       }, "html");


update_fetcher("/lbnerc/control/recent20run", 1000,
	       function(data) {
		   $('#recent20run').html(data);
	       }, "html");
