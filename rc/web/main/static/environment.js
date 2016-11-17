var upfreq=10000; // how often to query (ms)
var chart0; // global
$(function() {
    chart0 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph0',
		events: {load: requestData0}
	       },
	title: {text: 'Low Voltage Power Supply Crate Power'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Power (W)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "LV Crate",data: []}
	]
    });
});

function requestData0() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.LV_P',
	datatype: "json",
	success: function(data) {
	    chart0.series[0].setData(JSON.parse(data));;
	    setTimeout(requestData0, upfreq);
	},
	cache: false
    });
};

var chart0a; // global
$(function() {
    chart0a = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph0a',
		events: {load: requestData0a}
	       },
	title: {text: 'High Voltage Power Supply Crate Power'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Power (W)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "HV Crate",data: []}
	]
    });
});

function requestData0a() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.Bias_P',
	datatype: "json",
	success: function(data) {
	    chart0a.series[0].setData(JSON.parse(data));;
	    setTimeout(requestData0a, upfreq);
	},
	cache: false
    });
};

var chart1; // global
$(function() {
    chart1 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph1',
		events: {load: requestData1}
	       },
	title: {text: 'PC4 Temperature (C)'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Temp(C)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [{
	    data: []
	}]
    });
});

function requestData1() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.Temperature',
	datatype: "json",
	success: function(data) {
	    chart1.series[0].setData(JSON.parse(data));
	    // call it again after 5 second
	    setTimeout(requestData1, 5000);
	},
	cache: false
    });
}
////////////////////////
var chart2; // global
$(function() {
    chart2 = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph2',
		events: {load: requestData2}
	       },
	title: {text: 'PC4 Relative Humidity'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Relative Humidity',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [{
	    data: []
	}]
    });
});

function requestData2() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.RelHum',
	datatype: "json",
	success: function(data) {
	    chart2.series[0].setData(JSON.parse(data));
	    // call it again after 5 second
	    setTimeout(requestData2, 5000);
	},
	cache: false
    });
}

var chart2a; // global
$(function() {
    chart2a = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph2a',
		events: {load: requestData2a}
	       },
	title: {text: 'GW01 server input air temp'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Temp (C)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [{
	    data: []
	}]
    });
});

function requestData2a() {
    $.ajax({
	url: '/lbnerc/control/moni/cputemps/lbne35t-gateway01',
	datatype: "json",
	success: function(data) {
	    chart2a.series[0].setData(JSON.parse(data));
	    // call it again after 5 second
	    setTimeout(requestData2a, 5000);
	},
	cache: false
    });
}


var chart3; // global
$(function() {
    chart3 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph3',
		events: {load: requestData3}
	       },
	title: {text: 'Optical Converter Supply Voltage'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Voltage (V)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "OPCON V",data: []}
	]
    });
});

function requestData3() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.OPTCONVBD_RB_V',
	datatype: "json",
	success: function(data) {
	    chart3.series[0].setData(JSON.parse(data));;
	    setTimeout(requestData3, upfreq);
	},
	cache: false
    });
};

var chart4; // global
$(function() {
    chart4 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph4',
		events: {load: requestData4}
	       },
	title: {text: 'Optical Converter Supply Current'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Current (A)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "OPCON I",data: []}
	]
    });
});

function requestData4() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.OPTCONVBD_RB_I',
	datatype: "json",
	success: function(data) {
	    chart4.series[0].setData(JSON.parse(data));;
	    setTimeout(requestData4, upfreq);
	},
	cache: false
    });
};

var chart5; // global
$(function() {
    chart5 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph5',
		events: {load: requestData5}
	       },
	title: {text: 'Cryostat Temperatures'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Temp (K)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "RTD1",data: []},
	    {name: "RTD2",data: []}
	]
    });
});

function requestData5() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.RTD1_TEMP_1',
	datatype: "json",
	success: function(data) {
	    chart5.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.RTD1_TEMP_2',
	datatype: "json",
	success: function(data) {
	    chart5.series[1].setData(JSON.parse(data));;
	    setTimeout(requestData5, upfreq);
	},
	cache: false
    });
};
    

