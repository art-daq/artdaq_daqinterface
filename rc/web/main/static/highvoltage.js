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
	title: {text: 'APA Drift Voltage(kV)'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Voltage(kV)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "Set Value",data: []},
	    {name: "Read Value",data: []}
	]
    });
});

function requestData0() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.HV_SET_KVOLTS',
	datatype: "json",
	success: function(data) {
	    chart0.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.HV_READ_KVOLTS',
	datatype: "json",
	success: function(data) {
	    chart0.series[1].setData(JSON.parse(data));;
	    // call it again after 5 second
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
	title: {text: 'APA Drift Current(uA)'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Current (uA)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "Limit Set Value",data: []},
	    {name: "Read Value",data: []}
	]
    });
});

function requestData0a() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.I_LIMIT_SET_UAMPS',
	datatype: "json",
	success: function(data) {
	    chart0a.series[0].setData(JSON.parse(data));;
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.I_READ_UAMPS',
	datatype: "json",
	success: function(data) {
	    chart0a.series[1].setData(JSON.parse(data));;
	    // call it again after 5 second
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
	title: {text: 'APA Bias Voltage - Collection Plane (V)'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Voltage(V)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "APA 1",data: []},
	    {name: "APA 2",data: []},
	    {name: "APA 3",data: []},
	    {name: "APA 4",data: []}
	]
    });
});

function requestData1() {
    names =['1','2','3','4'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.APA' + name + '_COLL_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart1.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		// setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
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
	title: {text: 'APA Bias Current- Collection Plane (nA)'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(nA)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "APA 1",data: []},
	    {name: "APA 2",data: []},
	    {name: "APA 3",data: []},
	    {name: "APA 4",data: []}
	]
    });
});
function requestData2() {
    names =['1','2','3','4'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.APA' + name + '_COLL_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart2.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		// setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
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
	title: {text: 'APA Bias Voltage - Grid Plane (V)'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Voltage(V)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "APA 1",data: []},
	    {name: "APA 2",data: []},
	    {name: "APA 3",data: []},
	    {name: "APA 4",data: []}
	]
    });
});

function requestData3() {
    names =['1','2','3','4'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.APA' + name + '_GRID_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart3.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		// setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
    });
    
}
////////////////////////
var chart4; // global
$(function() {
    chart4 = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph4',
		events: {load: requestData4}
	       },
	title: {text: 'APA Bias Current- Grid Plane (nA)'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(nA)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "APA 1",data: []},
	    {name: "APA 2",data: []},
	    {name: "APA 3",data: []},
	    {name: "APA 4",data: []}
	]
    });
});
function requestData4() {
    names =['1','2','3','4'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.APA' + name + '_GRID_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart4.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		// setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
    });
}

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
	title: {text: 'APA Bias Voltage - U Plane (V)'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Voltage(V)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "APA 1",data: []},
	    {name: "APA 2",data: []},
	    {name: "APA 3",data: []},
	    {name: "APA 4",data: []}
	]
    });
});

function requestData5() {
    names =['1','2','3','4'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.APA' + name + '_U_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart5.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		// setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
    });
    
}
////////////////////////
var chart6; // global
$(function() {
    chart6 = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph6',
		events: {load: requestData6}
	       },
	title: {text: 'APA Bias Current- U Plane (nA)'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(nA)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "APA 1",data: []},
	    {name: "APA 2",data: []},
	    {name: "APA 3",data: []},
	    {name: "APA 4",data: []}
	]
    });
});
function requestData6() {
    names =['1','2','3','4'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.APA' + name + '_U_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart6.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		// setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
    });
}


var chart7; // global
$(function() {
    chart7 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph7',
		events: {load: requestData7}
	       },
	title: {text: 'APA Bias Voltages - Diverters, Fieldcage (V)'},
	xAxis: {type: 'datetime',minRange: 2000, maxRange: 5000},
	yAxis: {
	    title: {
		text: 'Voltage(V)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "DIVERTER1",data: []},
	    {name: "DIVERTER2",data: []},
	    {name: "FIELDCAGE",data: []}
	]
    });
});

function requestData7() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.DIVERTER1_RB_V',
	datatype: "json",
	success: function(data) {
	    chart7.series[0].setData(JSON.parse(data));;
	    // setTimeout(requestData1, upfreq);
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.DIVERTER2_RB_V',
	datatype: "json",
	success: function(data) {
	    chart7.series[1].setData(JSON.parse(data));;
	    // setTimeout(requestData1, upfreq);
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.FIELDCAGE_RB_V',
	datatype: "json",
	success: function(data) {
	    chart7.series[2].setData(JSON.parse(data));;
	    // setTimeout(requestData1, upfreq);
	},
	cache: false
    });
}
////////////////////////
var chart8; // global
$(function() {
    chart8 = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph8',
		events: {load: requestData8}
	       },
	title: {text: 'APA Bias Current- Diverters, Fieldcage (nA)'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(nA)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "DIVERTER1",data: []},
	    {name: "DIVERTER2",data: []},
	    {name: "FIELDCAGE",data: []}
	]
    });
});
function requestData8() {
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.DIVERTER1_RB_I',
	datatype: "json",
	success: function(data) {
	    chart8.series[0].setData(JSON.parse(data));;
	    // setTimeout(requestData1, upfreq);
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.DIVERTER2_RB_I',
	datatype: "json",
	success: function(data) {
	    chart8.series[1].setData(JSON.parse(data));;
	    // setTimeout(requestData1, upfreq);
	},
	cache: false
    });
    $.ajax({
	url: '/lbnerc/control/moni/hvcryo/35T.FIELDCAGE_RB_I',
	datatype: "json",
	success: function(data) {
	    chart8.series[2].setData(JSON.parse(data));;
	    // setTimeout(requestData1, upfreq);
	},
	cache: false
    });
}
