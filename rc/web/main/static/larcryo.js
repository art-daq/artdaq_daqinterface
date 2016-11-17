var upfreq=10000; // how often to query (ms)

var chart0; // global
$(function() {
    chart0 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'largraph0',
		events: {load: requestData0}
	       },
	title: {text: 'Purity Monitor  - Anode Drift Time'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Anode Drift Time (microsec)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    //{name: "PRM 0",data: []},
	    {name: "PRM 1",data: []},
	    {name: "PRM 2",data: []},
	    {name: "PRM 3",data: []},
	    {name: "PRM 4",data: []}
	]
    });
});

function requestData0() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_ANODETIME_1',
	datatype: "json",
	success: function(data) {
	    chart0.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_ANODETIME_2',
	datatype: "json",
	success: function(data) {
	    chart0.series[1].setData(JSON.parse(data));;
	},
	cache: false
   });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_ANODETIME_3',
	datatype: "json",
	success: function(data) {
	    chart0.series[2].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_ANODETIME_4',
	datatype: "json",
	success: function(data) {
	    chart0.series[3].setData(JSON.parse(data));;
	    setTimeout(requestData0, upfreq);
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
		renderTo: 'largraph1',
		events: {load: requestData1}
	       },
	title: {text: 'Purity Monitor - Electron Lifetime'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    max: 12500,
	    title: {
		text: 'Lifetime (microsec)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    //{name: "PRM 0",data: []},
	    {name: "PRM 1",data: []},
	    {name: "PRM 2",data: []},
	    {name: "PRM 3",data: []},
	    {name: "PRM 4",data: []}
	]
    });
});

function requestData1() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_LIFETIME_1',
	datatype: "json",
	success: function(data) {
	    chart1.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
    	url: '/lbnerc/control/moni/hvcryo/35T.PRM_LIFETIME_2',
    	datatype: "json",
    	success: function(data) {
    	    chart1.series[1].setData(JSON.parse(data));;
    	},
    	cache: false
    });
    $.ajax({
    	url: '/lbnerc/control/moni/hvcryo/35T.PRM_LIFETIME_3',
    	datatype: "json",
    	success: function(data) {
    	    chart1.series[2].setData(JSON.parse(data));;
    	},
    	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_LIFETIME_4',
	datatype: "json",
	success: function(data) {
	    chart1.series[3].setData(JSON.parse(data));;
	    setTimeout(requestData1, upfreq);
	},
	cache: false
    });
    
};

var chart2; // global
$(function() {
    chart2 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'largraph2',
		events: {load: requestData2}
	       },
	title: {text: 'Purity Monitor - Impurities'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Impurities ()',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    //{name: "PRM 0",data: []},
	    {name: "PRM 1",data: []},
	    {name: "PRM 2",data: []},
	    {name: "PRM 3",data: []},
	    {name: "PRM 4",data: []}
	]
    });
});

function requestData2() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_IMPURITIES_1',
	datatype: "json",
	success: function(data) {
	    chart2.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
    	url: '/lbnerc/control/moni/hvcryo/35T.PRM_IMPURITIES_2',
    	datatype: "json",
    	success: function(data) {
    	    chart2.series[1].setData(JSON.parse(data));;
    	},
    	cache: false
    });
    $.ajax({
    	url: '/lbnerc/control/moni/hvcryo/35T.PRM_IMPURITIES_3',
    	datatype: "json",
    	success: function(data) {
    	    chart2.series[2].setData(JSON.parse(data));;
    	},
    	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.PRM_IMPURITIES_4',
	datatype: "json",
	success: function(data) {
	    chart2.series[3].setData(JSON.parse(data));;
	    setTimeout(requestData2, upfreq);
	},
	cache: false
    });
    
};

var chart3; // global
$(function() {
    chart3 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'largraph3',
		events: {load: requestData3}
	       },
	title: {text: 'LAr Pump Power'},
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
	    {name: "LAr Pump power",data: []}
	]
    });
});

function requestData3() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.VFD_TRUE_Power',
	datatype: "json",
	success: function(data) {
	    chart3.series[0].setData(JSON.parse(data));;
	    setTimeout(requestData3, upfreq);
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

var chart4; // global
$(function() {
    chart4 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'largraph4',
		events: {load: requestData4}
	       },
	title: {text: 'LAr Pump Accelerometer Data'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: ' ',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "Accelerometer RMS",data: []},
	    {name: "Accelerometer RPM",data: []}
	]
    });
});

function requestData4() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.ACCEL_RMS',
	datatype: "json",
	success: function(data) {
	    chart4.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.ACCEL_RPM',
	datatype: "json",
	success: function(data) {
	    chart4.series[1].setData(JSON.parse(data));;
	    setTimeout(requestData4, upfreq);
	},
	cache: false
    });
};
