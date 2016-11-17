var upfreq=600000; // how often to query (ms)
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
	title: {text: 'APA LowVoltage Voltage- Channel A'},
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
	    {name: "0A",data: []},
	    {name: "1A",data: []},
	    {name: "2A",data: []},
	    {name: "3A",data: []},
	    {name: "4A",data: []},
	    {name: "5A",data: []},
	    {name: "6A",data: []},
	    {name: "7A",data: []},
	    {name: "8A",data: []},
	    {name: "9A",data: []},
	    {name: "10A",data: []},
	    {name: "11A",data: []},
	    {name: "12A",data: []},
	    {name: "13A",data: []},
	    {name: "14A",data: []},
	    {name: "15A",data: []}
	]
    });
});

function requestData1() {
    names =['00A','01A','02A','03A','04A','05A','06A','07A','08A','09A','10A','11A','12A','13A','14A','15A'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_V',
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
	title: {text: 'APA LowVoltage Voltage- Channel B'},
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
	    {name: "0B",data: []},
	    {name: "1B",data: []},
	    {name: "2B",data: []},
	    {name: "3B",data: []},
	    {name: "4B",data: []},
	    {name: "5B",data: []},
	    {name: "6B",data: []},
	    {name: "7B",data: []},
	    {name: "8B",data: []},
	    {name: "9B",data: []},
	    {name: "10B",data: []},
	    {name: "11B",data: []},
	    {name: "12B",data: []},
	    {name: "13B",data: []},
	    {name: "14B",data: []},
	    {name: "15B",data: []}
	]
    });
});

function requestData3() {
    names =['00B','01B','02B','03B','04B','05B','06B','07B','08B','09B','10B','11B','12B','13B','14B','15B'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart3.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		//setTimeout(requestData3, upfreq);
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
	title: {text: 'APA LowVoltage Voltage- Channel C'},
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
	    {name: "0C",data: []},
	    {name: "1C",data: []},
	    {name: "2C",data: []},
	    {name: "3C",data: []},
	    {name: "4C",data: []},
	    {name: "5C",data: []},
	    {name: "6C",data: []},
	    {name: "7C",data: []},
	    {name: "8C",data: []},
	    {name: "9C",data: []},
	    {name: "10C",data: []},
	    {name: "11C",data: []},
	    {name: "12C",data: []},
	    {name: "13C",data: []},
	    {name: "14C",data: []},
	    {name: "15C",data: []}
	]
    });
});

function requestData5() {
    names =['00C','01C','02C','03C','04C','05C','06C','07C','08C','09C','10C','11C','12C','13C','14C','15C'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart5.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		//setTimeout(requestData5, upfreq);
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
	title: {text: 'APA LowVoltage Voltage- Channel D'},
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
	    {name: "0D",data: []},
	    {name: "1D",data: []},
	    {name: "2D",data: []},
	    {name: "3D",data: []},
	    {name: "4D",data: []},
	    {name: "5D",data: []},
	    {name: "6D",data: []},
	    {name: "7D",data: []},
	    {name: "8D",data: []},
	    {name: "9D",data: []},
	    {name: "10D",data: []},
	    {name: "11D",data: []},
	    {name: "12D",data: []},
	    {name: "13D",data: []},
	    {name: "14D",data: []},
	    {name: "15D",data: []}
	]
    });
});

function requestData7() {
    names =['00D','01D','02D','03D','04D','05D','06D','07D','08D','09D','10D','11D','12D','13D','14D','15D'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart7.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		//setTimeout(requestData7, upfreq);
	    },
	    cache: false
	});
    });
    
}

var chart9; // global
$(function() {
    chart9 = new Highcharts.StockChart({
	width: 100,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph9',
		events: {load: requestData9}
	       },
	title: {text: 'APA LowVoltage Voltage- Channel E'},
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
	    {name: "0E",data: []},
	    {name: "1E",data: []},
	    {name: "2E",data: []},
	    {name: "3E",data: []},
	    {name: "4E",data: []},
	    {name: "5E",data: []},
	    {name: "6E",data: []},
	    {name: "7E",data: []},
	    {name: "8E",data: []},
	    {name: "9E",data: []},
	    {name: "10E",data: []},
	    {name: "11E",data: []},
	    {name: "12E",data: []},
	    {name: "13E",data: []},
	    {name: "14E",data: []},
	    {name: "15E",data: []}
	]
    });
});

function requestData9() {
    names =['00E','01E','02E','03E','04E','05E','06E','07E','08E','09E','10E','11E','12E','13E','14E','15E'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_V',
	    datatype: "json",
	    success: function(data) {
		chart9.series[i].setData(JSON.parse(data));;
		// call it again after 5 second
		//setTimeout(requestData9, upfreq);
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
	title: {text: 'APA LowVoltage Current- Channel A'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(A)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "0A",data: []},
	    {name: "1A",data: []},
	    {name: "2A",data: []},
	    {name: "3A",data: []},
	    {name: "4A",data: []},
	    {name: "5A",data: []},
	    {name: "6A",data: []},
	    {name: "7A",data: []},
	    {name: "8A",data: []},
	    {name: "9A",data: []},
	    {name: "10A",data: []},
	    {name: "11A",data: []},
	    {name: "12A",data: []},
	    {name: "13A",data: []},
	    {name: "14A",data: []},
	    {name: "15A",data: []}
	]
    });
});
function requestData2() {
    names =['00A','01A','02A','03A','04A','05A','06A','07A','08A','09A','10A','11A','12A','13A','14A','15A'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart2.series[i].setData(JSON.parse(data));;
		//setTimeout(requestData1, upfreq);
	    },
	    cache: false
	});
    });
    
}

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
	title: {text: 'APA LowVoltage Current- Channel B'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(A)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "0B",data: []},
	    {name: "1B",data: []},
	    {name: "2B",data: []},
	    {name: "3B",data: []},
	    {name: "4B",data: []},
	    {name: "5B",data: []},
	    {name: "6B",data: []},
	    {name: "7B",data: []},
	    {name: "8B",data: []},
	    {name: "9B",data: []},
	    {name: "10B",data: []},
	    {name: "11B",data: []},
	    {name: "12B",data: []},
	    {name: "13B",data: []},
	    {name: "14B",data: []},
	    {name: "15B",data: []}
	]
    });
});
function requestData4() {
    names =['00B','01B','02B','03B','04B','05B','06B','07B','08B','09B','10B','11B','12B','13B','14B','15B'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart4.series[i].setData(JSON.parse(data));;
		//setTimeout(requestData4, upfreq);
	    },
	    cache: false
	});
    });
    
}


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
	title: {text: 'APA LowVoltage Current- Channel C'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(A)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "0C",data: []},
	    {name: "1C",data: []},
	    {name: "2C",data: []},
	    {name: "3C",data: []},
	    {name: "4C",data: []},
	    {name: "5C",data: []},
	    {name: "6C",data: []},
	    {name: "7C",data: []},
	    {name: "8C",data: []},
	    {name: "9C",data: []},
	    {name: "10C",data: []},
	    {name: "11C",data: []},
	    {name: "12C",data: []},
	    {name: "13C",data: []},
	    {name: "14C",data: []},
	    {name: "15C",data: []}
	]
    });
});
function requestData6() {
    names =['00C','01C','02C','03C','04C','05C','06C','07C','08C','09C','10C','11C','12C','13C','14C','15C'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart6.series[i].setData(JSON.parse(data));;
		//setTimeout(requestData6, upfreq);
	    },
	    cache: false
	});
    });
    
}


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
	title: {text: 'APA LowVoltage Current- Channel D'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(A)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "0D",data: []},
	    {name: "1D",data: []},
	    {name: "2D",data: []},
	    {name: "3D",data: []},
	    {name: "4D",data: []},
	    {name: "5D",data: []},
	    {name: "6D",data: []},
	    {name: "7D",data: []},
	    {name: "8D",data: []},
	    {name: "9D",data: []},
	    {name: "10D",data: []},
	    {name: "11D",data: []},
	    {name: "12D",data: []},
	    {name: "13D",data: []},
	    {name: "14D",data: []},
	    {name: "15D",data: []}
	]
    });
});
function requestData8() {
    names =['00D','01D','02D','03D','04D','05D','06D','07D','08D','09D','10D','11D','12D','13D','14D','15D'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart8.series[i].setData(JSON.parse(data));;
		//setTimeout(requestData8, upfreq);
	    },
	    cache: false
	});
    });
    
}


var chart10; // global
$(function() {
    chart10 = new Highcharts.StockChart({
	width: 400,
	height: 120,
	tooltip: { enabled: true },
	chart: {zoomType: 'x',
		animation: false,
		renderTo: 'graph10',
		events: {load: requestData10}
	       },
	title: {text: 'APA LowVoltage Current- Channel E'},
	xAxis: {type: 'datetime',minRange: 2000},
	yAxis: {
	    title: {
		text: 'Current(A)',
	    }
	},
	rangeSelector: {enabled:false},
	navigator: {enabled:false},
	scrollbar: {enabled:false},
	exporting: {enabled:true},
	series: [
	    {name: "0E",data: []},
	    {name: "1E",data: []},
	    {name: "2E",data: []},
	    {name: "3E",data: []},
	    {name: "4E",data: []},
	    {name: "5E",data: []},
	    {name: "6E",data: []},
	    {name: "7E",data: []},
	    {name: "8E",data: []},
	    {name: "9E",data: []},
	    {name: "10E",data: []},
	    {name: "11E",data: []},
	    {name: "12E",data: []},
	    {name: "13E",data: []},
	    {name: "14E",data: []},
	    {name: "15E",data: []}
	]
    });
});
function requestData10() {
    names =['00E','01E','02E','03E','04E','05E','06E','07E','08E','09E','10E','11E','12E','13E','14E','15E'], 
    $.each(names,function (i, name) {
	$.ajax({
	    url: '/lbnerc/control/moni/hvcryo/35T.RCE' + name + '_RB_I',
	    datatype: "json",
	    success: function(data) {
		chart10.series[i].setData(JSON.parse(data));;
		//setTimeout(requestData10, upfreq);
	    },
	    cache: false
	});
    });
    
}



